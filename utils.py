import random
import re
import requests
from flask import current_app, session
from flask_mail import Message
from extensions import mail


# ---------------- OTP ----------------

def generate_otp(length=6):
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def send_email_otp(to_email, otp_code, purpose="verify your account"):
    """Send an OTP by email. Requires MAIL_USERNAME/MAIL_PASSWORD in .env (free Gmail app password)."""
    subject = "Your AI.WITH CRAZZYYY verification code"
    body = (
        f"Your one-time code to {purpose} is: {otp_code}\n\n"
        f"This code expires in {current_app.config['OTP_EXPIRY_MINUTES']} minutes.\n"
        f"If you did not request this, you can safely ignore this email."
    )
    if not current_app.config.get("MAIL_USERNAME"):
        # No SMTP configured yet — log it so development still works end-to-end.
        current_app.logger.warning(
            f"[DEV MODE - no MAIL_USERNAME set] OTP for {to_email}: {otp_code}"
        )
        return False
    try:
        msg = Message(subject=subject, recipients=[to_email], body=body)
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f"Failed to send email OTP: {exc}")
        return False


def send_sms_otp(phone_number, otp_code):
    """Send an OTP by SMS using Fast2SMS's free-tier API (India numbers).
    Requires FAST2SMS_API_KEY in .env. Sign up free at https://www.fast2sms.com/
    """
    api_key = current_app.config.get("FAST2SMS_API_KEY")
    if not api_key:
        current_app.logger.warning(
            f"[DEV MODE - no FAST2SMS_API_KEY set] SMS OTP for {phone_number}: {otp_code}"
        )
        return False
    try:
        resp = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": api_key},
            data={
                "variables_values": otp_code,
                "route": "otp",
                "numbers": phone_number,
            },
            timeout=10,
        )
        return resp.status_code == 200 and resp.json().get("return") is True
    except Exception as exc:
        current_app.logger.error(f"Failed to send SMS OTP: {exc}")
        return False


# ---------------- password strength ----------------

def password_strength_errors(password):
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        errors.append("one special character")
    return errors


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


# ---------------- free, zero-config math captcha ----------------

def new_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    session["captcha_answer"] = a + b
    return f"{a} + {b}"


def check_captcha(user_answer):
    expected = session.pop("captcha_answer", None)
    try:
        return expected is not None and int(user_answer) == int(expected)
    except (TypeError, ValueError):
        return False
