lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from ..services.login_services import logout as logout_service, login as login_service, register as register_service
lazy from flask_login import current_user
lazy from flask_login import login_required
lazy from flask import current_app
lazy from ..services.schedule_services import get_my_schedule, create_my_schedule
lazy from ..models.Appointment import Appointment
lazy from ..services.appointment_services import (
    confirm_appointment as confirm_appointment_service,
    reject_appointment as reject_appointment_service,
    reschedule_appointment as reschedule_appointment_service,
    cancel_appointment as cancel_appointment_service,
)
lazy from datetime import datetime
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
            flash("Your schedule is ready. You can now receive appointment requests.", "success")
        except ValueError as e:
            flash(f"An error has occured: {e}", "error")
        except Exception as e:
            flash(f"An error has occured: {e}", "error")


    return redirect(url_for("contractor.dashboard"))

@contractor_bp.route("/confirm_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def confirm_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("The appointment was not found!", "error")
            return redirect(url_for("contractor.dashboard"))
        try:
            if not confirm_appointment_service(appointment=appointment):
                flash("The appointment couldn't be confirmed. Check for conflicts and the daily appointment limit.", "error")
        except Exception as e:
            current_app.logger.exception(e)
            flash("The appointment could not be confirmed!", "error")
            return redirect(url_for("contractor.dashboard"))

    return redirect(url_for("contractor.dashboard"))

@contractor_bp.route("/reject_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def reject_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("The appointment was not found!", "error")
            return redirect(url_for("contractor.dashboard"))

        try:
            if not reject_appointment_service(appointment=appointment):
                flash("The appointment could not be rejected.", "error")
        except Exception as e:
            current_app.logger.exception(e)
            flash("The appointment failed to be rejected", "error")
            return redirect(url_for("contractor.dashboard"))

    return redirect(url_for("contractor.dashboard"))

@contractor_bp.route("/reschedule_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def reschedule_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("The appointment was not found", "error")
            return redirect(url_for("contractor.dashboard"))
        try:
            start_time = datetime.fromisoformat(request.form.get("start_time", ""))
            end_time = datetime.fromisoformat(request.form.get("end_time", ""))
            if reschedule_appointment_service(appointment=appointment, new_start=start_time, new_end=end_time):
                flash("The appointment was successfully rescheduled!", "success")
        except ValueError as e:
            current_app.logger.exception(e)
            flash("Please enter valid start and end dates and times, with the end after the start.", "error")
            return redirect(url_for("contractor.dashboard"))
        except Exception as e:
            current_app.logger.exception(e)
            flash("The appointment could not successfully be rescheduled", "error")
            return redirect(url_for("contractor.dashboard"))

    return redirect(url_for("contractor.dashboard"))

@contractor_bp.route("/cancel_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("The apointment was not found", "error")
            return redirect(url_for("contractor.dashboard"))

        try:
            if cancel_appointment_service(appointment=appointment):
                flash("The appointment was successfully cancelled", "success")
        except Exception as e:
            current_app.logger.exception(e)
            flash("The appointment could not be cancelled!", "error")
            return redirect(url_for("contractor.dashboard"))
    return redirect(url_for("contractor.dashboard"))
