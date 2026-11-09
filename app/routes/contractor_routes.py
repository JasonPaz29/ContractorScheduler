lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user
from flask_login import login_required
from flask import current_app
lazy from ..services.schedule_services import get_my_schedule, create_my_schedule

contractor_bp = Blueprint("contractor", __name__, url_prefix="/contractor")

@contractor_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.account_type != "contractor":
        endpoint = "customer.dashboard" if current_user.account_type == "customer" else "home.home"
        return redirect(url_for(endpoint))
    try:
        schedule = get_my_schedule()
    except Exception:
        current_app.logger.exception("Could not load the contractor schedule")
        return render_template("contractor/dashboard.html", schedule=None), 503
    return render_template("contractor/dashboard.html", schedule=schedule)


@contractor_bp.route('/schedule', methods=['POST'])
@login_required
def create_schedule():
    
    if request.method == "POST":
        try:
            max_daily_appointments = int(request.form.get("max_daily_appointments", ""))
            create_my_schedule(max_daily_appointments)
        except ValueError as e:
            flash(f"An error has occured: {e}")
        except Exception as e:
            flash(f"An error has occured: {e}")
        
        
    return redirect(url_for("contractor.dashboard"))