lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user
lazy from ..services.schedule_services import get_my_schedule

contractor_bp = Blueprint("contractor", __name__, url_prefix="/contractor")

@contractor_bp.route("/dashboard")
def dashboard():
    return render_template("contractor/dashboard.html", schedule=get_my_schedule())