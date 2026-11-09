lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user
from flask_login import login_required
from flask import current_app
lazy from ..services.schedule_services import get_booking_schedule

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.account_type != "customer":
        endpoint = "contractor.dashboard" if current_user.account_type == "contractor" else "home.home"
        return redirect(url_for(endpoint))
    try:
        schedule = get_booking_schedule()
    except Exception:
        current_app.logger.exception("Could not load the booking schedule")
        return render_template("customer/dashboard.html", schedule=None), 503
    return render_template("customer/dashboard.html", schedule=schedule)
