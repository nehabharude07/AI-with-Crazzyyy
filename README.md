# AI.WITH CRAZZYYY — business website

A Flask website for an AI/ML/GenAI/Python business, with a collapsible sidebar,
full authentication (email OTP, 2FA, Google login), role-based dashboard with
charts, and a customer reviews system.

## Quick start

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
# edit .env — see "Setting up OTP / Google login" below

# 4. Create the database + demo data
export FLASK_APP=app.py         # on Windows: set FLASK_APP=app.py
flask seed-db

# 5. Run
python app.py
```

Open **http://127.0.0.1:5000**.

**Demo admin login:** `admin@aiwithcrazzyy.dev` / `Admin@12345`
(change this password immediately in a real deployment — it's only for you to see the dashboard).

## What's included

- **Public site**: Home, About Us, Services, Projects, Reviews, Contact Us — collapsible sidebar (hamburger toggle below 900px width).
- **Registration**: name/email/password + optional phone, math captcha, password-strength validation, email OTP verification before the account is usable.
- **Login**: password + captcha, account lockout after 5 failed attempts (15 min), optional 2FA (email/SMS OTP) gate before a session is granted.
- **Google Sign-In**: one-click login/registration via OAuth (needs your own free Google Cloud credentials — see below).
- **Forgot/reset password**: emailed, time-limited (30 min) reset link.
- **Account page** (`/auth/profile`): toggle 2FA on/off, see recent login history.
- **Role-based dashboard** (`/dashboard`, admin/manager only): stat cards, a pie chart (projects by category), a bar chart (avg. delivery time by category), a line chart (deliveries per month), and a full project table.
- **Reviews** (`/reviews`): anyone can read approved reviews; anyone (guest or logged in) can submit one with a star rating.
- **Security**: bcrypt password hashing, CSRF protection on every form, per-route rate limiting, secure session cookies, SQL injection protection via the ORM, Jinja auto-escaping against XSS, audit log of every login attempt (`LoginLog` table).

## Setting up OTP / Google login (all free)

The site runs immediately with **no external accounts** — OTP codes just print to your terminal
(`[DEV MODE] OTP for ...: 123456`) instead of being emailed/texted, so you can still test every flow locally.
To get **real** codes delivered:

### Email OTP (Gmail, free)
1. Turn on 2-Step Verification: https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords
3. In `.env`, set `MAIL_USERNAME` to your Gmail address and `MAIL_PASSWORD` to the 16-character app password.

### Real SMS OTP to a phone (Fast2SMS, free tier, India numbers)
1. Sign up free: https://www.fast2sms.com/ → Dev API → copy your API key.
2. In `.env`, set `FAST2SMS_API_KEY`.
3. Users who enter a phone number at registration will get OTPs by SMS as well as email.

> No other SMS provider is wired in. If you're outside India or want a different provider (Twilio, MSG91, etc.), swap the request in `send_sms_otp()` inside `utils.py` — it's one function.

### Google Sign-In (Google Cloud, free)
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth Client ID (type: Web application).
3. Add authorized redirect URI: `http://127.0.0.1:5000/auth/google/callback` (add your real domain's equivalent once deployed).
4. In `.env`, set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

## Project structure

```
aiwithcrazzyy/
├── app.py                   App factory, marketing routes, `flask seed-db` command
├── config.py                All settings, read from .env
├── extensions.py             Shared extension instances (db, login, mail, etc.)
├── models.py                 User, LoginLog, Review, Project
├── utils.py                   OTP generation, email/SMS sending, password/captcha checks
├── decorators.py              @role_required(...) for RBAC
├── blueprints/
│   ├── auth.py                register / login / OTP / 2FA / reset / Google OAuth
│   ├── dashboard.py            chart data + RBAC-protected dashboard route
│   └── reviews.py              view + submit reviews
├── templates/
│   ├── base.html               shared sidebar layout (auth-aware nav)
│   ├── auth/                   register, login, verify_otp, forgot/reset password, profile
│   ├── dashboard/index.html    charts (Chart.js via CDN)
│   ├── reviews/list.html
│   └── home/about/services/projects/contact.html
├── static/css/style.css        gold-on-black theme, all design tokens as CSS variables
├── requirements.txt
└── .env.example
```

## Customizing

- **Roles**: `admin`, `manager`, `employee`, `user` (see `models.ROLES`). Change a user's role directly in the database, or add an admin-only "manage users" page later.
- **Dashboard data**: currently reads from the `Project` table. Add real projects via a Python shell, a script, or build an admin form — the charts recompute automatically from whatever's in the table.
- **Reviews**: auto-approved by default (`Review.approved`). Flip that default and add an admin moderation view if you want to check reviews before they go live.
- **Colors/fonts**: CSS variables at the top of `static/css/style.css`.

## Deploying

Don't use `app.run(debug=True)` in production. Use gunicorn behind HTTPS, and set `FORCE_HTTPS=true` in `.env`:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Also switch `DATABASE_URL` to a real database (Postgres/MySQL) instead of SQLite for anything beyond a demo.
