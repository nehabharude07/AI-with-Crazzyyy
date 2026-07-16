from datetime import datetime, timedelta
from flask_login import UserMixin
from extensions import db, bcrypt

ROLES = ["admin", "manager", "employee", "user"]


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)  # nullable for Google-only accounts
    role = db.Column(db.String(20), default="user", nullable=False)

    is_verified = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)

    google_id = db.Column(db.String(120), unique=True, nullable=True)

    # OTP fields (shared by email-verify / 2FA / password reset flows)
    otp_code = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    otp_purpose = db.Column(db.String(30), nullable=True)  # register | login_2fa | reset_password

    # account protection
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def register_failed_attempt(self, max_attempts, lockout_minutes):
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def reset_login_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None

    def set_otp(self, code, purpose, expiry_minutes):
        self.otp_code = code
        self.otp_purpose = purpose
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    def verify_otp(self, code, purpose):
        if not self.otp_code or not self.otp_expiry:
            return False
        if self.otp_purpose != purpose:
            return False
        if datetime.utcnow() > self.otp_expiry:
            return False
        return self.otp_code == code

    def clear_otp(self):
        self.otp_code = None
        self.otp_expiry = None
        self.otp_purpose = None

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class LoginLog(db.Model):
    __tablename__ = "login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    email_attempted = db.Column(db.String(160), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success | failed | locked
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="login_logs")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=True)  # auto-approved by default
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="reviews")


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    client_name = db.Column(db.String(160), nullable=True)
    category = db.Column(db.String(60), nullable=False)  # e.g. GenAI, ML, Automation, Python Dev, Mentorship
    status = db.Column(db.String(30), default="delivered")  # delivered | in_progress | delayed
    start_date = db.Column(db.Date, nullable=False)
    delivered_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def delivery_days(self):
        if self.delivered_date and self.start_date:
            return (self.delivered_date - self.start_date).days
        return None
