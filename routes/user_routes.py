# routes/user.py
from flask import Blueprint, render_template, request, flash
from library_service import get_patron_status_report

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    patron_id = ""
    report = None
    if request.method == "POST":
        patron_id = (request.form.get("patron_id") or "").strip()
        report = get_patron_status_report(patron_id)
        if "error" in report:
            flash(report["error"], "error")
            report = None
    return render_template("patron_profile.html", patron_id=patron_id, report=report)
