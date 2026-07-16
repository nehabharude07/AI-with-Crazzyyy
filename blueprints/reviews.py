from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from extensions import db, limiter
from models import Review
from utils import is_valid_email

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews")


@reviews_bp.route("/", methods=["GET"])
def list_reviews():
    reviews = Review.query.filter_by(approved=True).order_by(Review.created_at.desc()).all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    return render_template(
        "reviews/list.html", active="reviews", reviews=reviews, avg_rating=avg_rating,
        review_count=len(reviews),
    )


@reviews_bp.route("/submit", methods=["POST"])
@limiter.limit("10 per hour")
def submit_review():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    rating = request.form.get("rating", "")
    comment = request.form.get("comment", "").strip()

    if current_user.is_authenticated:
        name = name or current_user.name
        email = email or current_user.email

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not is_valid_email(email):
        errors.append("Please enter a valid email address.")
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        errors.append("Please choose a rating between 1 and 5.")
        rating = None
    if not comment or len(comment) < 5:
        errors.append("Please write a short review (at least 5 characters).")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("reviews.list_reviews"))

    review = Review(
        user_id=current_user.id if current_user.is_authenticated else None,
        name=name,
        email=email,
        rating=rating,
        comment=comment,
        approved=True,
    )
    db.session.add(review)
    db.session.commit()
    flash("Thanks! Your review has been posted.", "success")
    return redirect(url_for("reviews.list_reviews"))
