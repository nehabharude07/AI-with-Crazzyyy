import json
from collections import defaultdict, Counter

from flask import Blueprint, render_template
from flask_login import login_required

from models import Project
from decorators import role_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
@role_required("admin", "manager")
def index():
    projects = Project.query.order_by(Project.start_date).all()

    # ---- pie chart: projects by category ----
    category_counts = Counter(p.category for p in projects)
    pie_labels = list(category_counts.keys())
    pie_values = list(category_counts.values())

    # ---- bar/column chart: average delivery time (days) per category ----
    delivery_by_category = defaultdict(list)
    for p in projects:
        if p.delivery_days is not None:
            delivery_by_category[p.category].append(p.delivery_days)
    bar_labels = list(delivery_by_category.keys())
    bar_values = [
        round(sum(v) / len(v), 1) if v else 0
        for v in delivery_by_category.values()
    ]

    # ---- line chart: projects delivered per month ----
    monthly_counts = defaultdict(int)
    for p in projects:
        if p.delivered_date:
            key = p.delivered_date.strftime("%Y-%m")
            monthly_counts[key] += 1
    line_labels = sorted(monthly_counts.keys())
    line_values = [monthly_counts[k] for k in line_labels]

    # ---- status breakdown ----
    status_counts = Counter(p.status for p in projects)

    delivered = [p for p in projects if p.delivered_date]
    avg_delivery = (
        round(sum(p.delivery_days for p in delivered) / len(delivered), 1)
        if delivered else 0
    )

    stats = {
        "total_projects": len(projects),
        "delivered_count": status_counts.get("delivered", 0),
        "in_progress_count": status_counts.get("in_progress", 0),
        "delayed_count": status_counts.get("delayed", 0),
        "avg_delivery_days": avg_delivery,
    }

    chart_data = {
        "pie": {"labels": pie_labels, "values": pie_values},
        "bar": {"labels": bar_labels, "values": bar_values},
        "line": {"labels": line_labels, "values": line_values},
    }

    return render_template(
        "dashboard/index.html",
        active="dashboard",
        stats=stats,
        chart_data=json.dumps(chart_data),
        projects=projects,
    )
