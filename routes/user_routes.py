from flask import Blueprint, render_template, request
from services.library_service import get_patron_status_report

user_bp = Blueprint("user", __name__)

@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    patron_id = request.form.get("patron_id") if request.method == "POST" else request.args.get("patron_id", "")
    report = get_patron_status_report(patron_id) if patron_id else None
    return render_template("patron_profile.html", patron_id=patron_id, report=report)
