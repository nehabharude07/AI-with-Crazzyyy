import os
from datetime import datetime, date, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import current_user
from dotenv import load_dotenv

load_dotenv()

from config import Config
from extensions import db, bcrypt, login_manager, mail, csrf, limiter, oauth
from models import User, Project, Review

# ---- static content for the marketing pages (unchanged from before) ----

SERVICES = [
    {"icon": "brain", "title": "Custom AI & ML Models",
     "desc": "Model design, training and evaluation tailored to your data, from classic ML pipelines to deep learning."},
    {"icon": "spark", "title": "Generative AI Integrations",
     "desc": "LLM-powered chatbots, RAG pipelines and multi-step agents built with LangChain and LangGraph on top of your own data and workflows."},
    {"icon": "code", "title": "Python Development",
     "desc": "Production-grade Python backends, APIs and automation scripts, built clean, tested and documented."},
    {"icon": "bars", "title": "Process Automation",
     "desc": "Replace manual, repetitive work with reliable scripts and pipelines that run themselves."},
    {"icon": "cap", "title": "AI/ML Mentorship & Training",
     "desc": "1:1 mentorship and cohort-based teaching for engineers and teams moving into AI and GenAI."},
    {"icon": "gauge", "title": "MLOps & Deployment",
     "desc": "Get models out of notebooks and into production with proper versioning, monitoring and CI/CD."},
]

PROJECTS_STATIC = [
    {"name": "DocuMind RAG Assistant", "tag": "GenAI / RAG",
     "desc": "An internal knowledge assistant that answers employee questions from thousands of scattered PDFs and wikis, built with LangChain.",
     "link": "#"},
    {"name": "ChurnGuard", "tag": "Machine Learning",
     "desc": "A churn-prediction model plugged straight into a CRM, flagging at-risk customers weeks in advance.",
     "link": "#"},
    {"name": "FlowBot Ops", "tag": "Automation",
     "desc": "A Python automation suite that replaced 14 hours a week of manual report building with a single scheduled job.",
     "link": "#"},
    {"name": "CodeMentor Cohort", "tag": "Education",
     "desc": "An 8-week cohort program that took 20 engineers from Python basics to shipping their first ML model.",
     "link": "#"},
    {"name": "SupportGPT Agent", "tag": "GenAI / Agentic",
     "desc": "A multi-step LangGraph support agent that triages tickets, pulls order data, and drafts replies for human approval.",
     "link": "#"},
    {"name": "PriceSense Engine", "tag": "Machine Learning",
     "desc": "A dynamic pricing model for an e-commerce client that adjusts prices in real time based on demand and stock levels.",
     "link": "#"},
    {"name": "InvoiceFlow", "tag": "Automation",
     "desc": "An end-to-end invoice extraction and reconciliation pipeline, cutting manual finance work by 70%.",
     "link": "#"},
    {"name": "DataPipe ETL", "tag": "Python Dev",
     "desc": "A production ETL system moving data reliably between five different business tools, with monitoring and alerts.",
     "link": "#"},
]

NAV_ITEMS = [
    {"id": "home", "label": "Home", "endpoint": "home"},
    {"id": "about", "label": "About Us", "endpoint": "about"},
    {"id": "services", "label": "Services", "endpoint": "services"},
    {"id": "projects", "label": "Projects", "endpoint": "projects"},
    {"id": "reviews", "label": "Reviews", "endpoint": "reviews.list_reviews"},
    {"id": "contact", "label": "Contact Us", "endpoint": "contact"},
]


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)

    if app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if app.config.get("FORCE_HTTPS"):
        @app.before_request
        def _force_https():
            if request.headers.get("X-Forwarded-Proto", "http") != "https":
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {"nav_items": NAV_ITEMS, "current_year": datetime.now().year}

    # ---- register blueprints ----
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.reviews import reviews_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reviews_bp)

    # ---- marketing pages ----

    @app.route("/")
    def home():
        return render_template("home.html", active="home", services=SERVICES[:4], testimonials=[])

    @app.route("/about")
    def about():
        return render_template("about.html", active="about")

    @app.route("/services")
    def services():
        return render_template("services.html", active="services", services=SERVICES)

    @app.route("/projects")
    def projects():
        return render_template("projects.html", active="projects", projects=PROJECTS_STATIC)

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            message = request.form.get("message", "").strip()
            if not name or not email or not message:
                flash("Please fill in your name, email and message before sending.", "error")
            else:
                app.logger.info(f"[New enquiry] {name} <{email}>: {message}")
                flash("Thanks! Your message has been sent — we'll reply within 1 business day.", "success")
            return redirect(url_for("contact"))
        return render_template("contact.html", active="contact")

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                                message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="That page doesn't exist."), 404

    # ---- CLI: seed demo data ----
    @app.cli.command("seed-db")
    def seed_db():
        """Create tables and populate demo admin user + sample projects."""
        db.create_all()

        if not User.query.filter_by(email="admin@aiwithcrazzyy.dev").first():
            admin = User(
                name="Studio Admin",
                email="admin@aiwithcrazzyy.dev",
                role="admin",
                is_verified=True,
            )
            admin.set_password("Admin@12345")
            db.session.add(admin)
            print("Created admin user: admin@aiwithcrazzyy.dev / Admin@12345")

        if Project.query.count() == 0:
            today = date.today()
            sample = [
                ("DocuMind RAG Assistant", "GenAI", 60, 12, "delivered"),
                ("ChurnGuard", "Machine Learning", 120, 21, "delivered"),
                ("FlowBot Ops", "Automation", 100, 9, "delivered"),
                ("CodeMentor Cohort", "Mentorship", 80, 30, "delivered"),
                ("PriceSense", "Machine Learning", 45, 18, "delivered"),
                ("SupportGPT", "GenAI", 30, 14, "delivered"),
                ("InvoiceFlow", "Automation", 20, 7, "delivered"),
                ("ResumeRanker", "Machine Learning", 15, None, "in_progress"),
                ("KnowledgeBot v2", "GenAI", 10, None, "in_progress"),
                ("DataPipe ETL", "Python Dev", 70, 25, "delivered"),
                ("Cohort Batch 4", "Mentorship", 40, None, "in_progress"),
                ("LegacyMigrate", "Python Dev", 90, 40, "delayed"),
            ]
            for name, category, start_days_ago, delivery_days, status in sample:
                start = today - timedelta(days=start_days_ago)
                delivered = (start + timedelta(days=delivery_days)) if delivery_days else None
                db.session.add(Project(
                    name=name, category=category, status=status,
                    start_date=start, delivered_date=delivered,
                    client_name="Confidential client",
                ))
            print("Added sample project data.")

        if Review.query.count() == 0:
            demo_reviews = [
                ("Priya Nair", "priya@example.com", 5,
                 "They took a vague idea and shipped a working GenAI assistant in three weeks."),
                ("Marcus Webb", "marcus@example.com", 5,
                 "Our reporting used to take a full day every week — now it runs itself."),
                ("Ananya Rao", "ananya@example.com", 4,
                 "The mentorship sessions were the clearest, most practical AI training I've had."),
            ]
            for name, email, rating, comment in demo_reviews:
                db.session.add(Review(name=name, email=email, rating=rating, comment=comment, approved=True))
            print("Added sample reviews.")

        db.session.commit()
        print("Database seeded.")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5109)