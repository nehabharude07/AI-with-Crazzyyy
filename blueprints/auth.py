from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, session, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from extensions import db, limiter, oauth
from models import User, LoginLog
from utils import (
    generate_otp, send_email_otp, send_sms_otp,
    password_strength_errors, is_valid_email, new_captcha, check_captcha,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _log_attempt(user, status):
    log = LoginLog(
        user_id=user.id if user else None,
        email_attempted=request.form.get("email"),
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        status=status,
    )
    db.session.add(log)
    db.session.commit()


# ---------------- registration ----------------

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        captcha_answer = request.form.get("captcha", "")

        errors = []
        if not check_captcha(captcha_answer):
            errors.append("The captcha answer was incorrect.")
        if not name:
            errors.append("Please enter your name.")
        if not is_valid_email(email):
            errors.append("Please enter a valid email address.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if password != confirm:
            errors.append("Passwords do not match.")
        pw_errors = password_strength_errors(password)
        if pw_errors:
            errors.append("Password must contain " + ", ".join(pw_errors) + ".")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", captcha_prompt=new_captcha(),
                                    name=name, email=email, phone=phone)

        user = User(name=name, email=email, phone=phone or None, role="user", is_verified=False)
        user.set_password(password)
        otp = generate_otp()
        user.set_otp(otp, "register", current_app.config["OTP_EXPIRY_MINUTES"])
        db.session.add(user)
        db.session.commit()

        if phone:
            send_sms_otp(phone, otp)
        send_email_otp(email, otp, purpose="verify your account")

        session["pending_user_id"] = user.id
        flash("We sent a verification code to your email" + (" and phone" if phone else "") + ".", "success")
        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html", captcha_prompt=new_captcha(), name="", email="", phone="")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def verify_otp():
    user_id = session.get("pending_user_id")
    if not user_id:
        flash("Please register or log in first.", "error")
        return redirect(url_for("auth.register"))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if user.verify_otp(code, "register"):
            user.is_verified = True
            user.clear_otp()
            db.session.commit()
            session.pop("pending_user_id", None)
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            _log_attempt(user, "success")
            flash("Your account is verified. Welcome!", "success")
            return redirect(url_for("home"))
        else:
            flash("That code is incorrect or has expired.", "error")

    return render_template("auth/verify_otp.html", email=user.email, purpose="account")


@auth_bp.route("/resend-otp")
@limiter.limit("5 per hour")
def resend_otp():
    user_id = session.get("pending_user_id")
    user = User.query.get(user_id) if user_id else None
    if not user:
        return redirect(url_for("auth.register"))
    otp = generate_otp()
    user.set_otp(otp, user.otp_purpose or "register", current_app.config["OTP_EXPIRY_MINUTES"])
    db.session.commit()
    if user.phone:
        send_sms_otp(user.phone, otp)
    send_email_otp(user.email, otp, purpose="verify your account")
    flash("A new code has been sent.", "success")
    return redirect(url_for("auth.verify_otp"))


# ---------------- login ----------------

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        captcha_answer = request.form.get("captcha", "")

        if not check_captcha(captcha_answer):
            flash("The captcha answer was incorrect.", "error")
            return render_template("auth/login.html", captcha_prompt=new_captcha(), email=email)

        user = User.query.filter_by(email=email).first()

        if user and user.is_locked():
            _log_attempt(user, "locked")
            minutes_left = max(1, int((user.locked_until - datetime.utcnow()).total_seconds() // 60))
            flash(f"This account is temporarily locked. Try again in about {minutes_left} minute(s).", "error")
            return render_template("auth/login.html", captcha_prompt=new_captcha(), email=email)

        if user and user.check_password(password):
            if not user.is_verified:
                session["pending_user_id"] = user.id
                otp = generate_otp()
                user.set_otp(otp, "register", current_app.config["OTP_EXPIRY_MINUTES"])
                db.session.commit()
                send_email_otp(user.email, otp, purpose="verify your account")
                flash("Please verify your account first — we've sent a new code.", "error")
                return redirect(url_for("auth.verify_otp"))

            user.reset_login_attempts()
            db.session.commit()

            if user.two_factor_enabled:
                otp = generate_otp()
                user.set_otp(otp, "login_2fa", current_app.config["OTP_EXPIRY_MINUTES"])
                db.session.commit()
                if user.phone:
                    send_sms_otp(user.phone, otp)
                send_email_otp(user.email, otp, purpose="confirm this login")
                session["pending_2fa_user_id"] = user.id
                session["remember_me"] = remember
                return redirect(url_for("auth.verify_login_otp"))

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            _log_attempt(user, "success")
            flash(f"Welcome back, {user.name.split(' ')[0]}.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home"))

        if user:
            user.register_failed_attempt(
                current_app.config["MAX_LOGIN_ATTEMPTS"], current_app.config["LOCKOUT_MINUTES"]
            )
            db.session.commit()
        _log_attempt(user, "failed")
        flash("Incorrect email or password.", "error")
        return render_template("auth/login.html", captcha_prompt=new_captcha(), email=email)

    return render_template("auth/login.html", captcha_prompt=new_captcha(), email="")


@auth_bp.route("/verify-login-otp", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def verify_login_otp():
    user_id = session.get("pending_2fa_user_id")
    user = User.query.get(user_id) if user_id else None
    if not user:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if user.verify_otp(code, "login_2fa"):
            user.clear_otp()
            remember = session.pop("remember_me", False)
            session.pop("pending_2fa_user_id", None)
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            _log_attempt(user, "success")
            flash("Login confirmed.", "success")
            return redirect(url_for("home"))
        flash("That code is incorrect or has expired.", "error")

    return render_template("auth/verify_otp.html", email=user.email, purpose="login", login_otp=True)


@auth_bp.route("/profile")
@login_required
def profile():
    from models import LoginLog
    recent_logs = (
        LoginLog.query.filter_by(user_id=current_user.id)
        .order_by(LoginLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return render_template("auth/profile.html", active="profile", recent_logs=recent_logs)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for("home"))


# ---------------- forgot / reset password ----------------

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = _serializer().dumps(email, salt="password-reset")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            from flask_mail import Message
            from extensions import mail
            try:
                msg = Message(
                    subject="Reset your AI.WITH CRAZZYYY password",
                    recipients=[email],
                    body=f"Click the link below to reset your password (valid for 30 minutes):\n\n{reset_url}",
                )
                mail.send(msg)
            except Exception as exc:
                current_app.logger.warning(f"[DEV MODE] Password reset link for {email}: {reset_url} ({exc})")
        # Always show the same message so we don't leak which emails exist
        flash("If that email is registered, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def reset_password(token):
    try:
        email = _serializer().loads(token, salt="password-reset", max_age=1800)
    except SignatureExpired:
        flash("This reset link has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("This reset link is invalid.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = password_strength_errors(password)
        if password != confirm:
            errors.append("passwords must match")
        if errors:
            flash("Password must contain " + ", ".join(errors) + ".", "error")
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        user.reset_login_attempts()
        db.session.commit()
        flash("Your password has been updated. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


# ---------------- Google OAuth ----------------

@auth_bp.route("/google/login")
def google_login():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Google sign-in isn't configured yet. Add GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET to .env.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return redirect(url_for("auth.login"))
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()
    except Exception as exc:
        current_app.logger.error(f"Google OAuth failed: {exc}")
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    google_id = userinfo["sub"]
    email = userinfo["email"].lower()
    name = userinfo.get("name", email.split("@")[0])

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(name=name, email=email, google_id=google_id, role="user", is_verified=True)
        db.session.add(user)
    else:
        user.google_id = google_id
        user.is_verified = True

    user.last_login = datetime.utcnow()
    db.session.commit()

    login_user(user)
    _log_attempt(user, "success")
    flash(f"Welcome, {user.name.split(' ')[0]}.", "success")
    return redirect(url_for("home"))


# ---------------- profile: toggle 2FA ----------------

@auth_bp.route("/toggle-2fa", methods=["POST"])
@login_required
def toggle_2fa():
    current_user.two_factor_enabled = not current_user.two_factor_enabled
    db.session.commit()
    state = "enabled" if current_user.two_factor_enabled else "disabled"
    flash(f"Two-factor authentication {state}.", "success")
    return redirect(request.referrer or url_for("home"))
