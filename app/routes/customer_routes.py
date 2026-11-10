lazy from flask import Blueprint, render_template, redirect, url_for, request, flash
lazy from datetime import datetime
lazy from flask_login import current_user
lazy from flask_login import login_required
lazy from flask import current_app
lazy from ..services.schedule_services import get_booking_schedule
lazy from ..services.appointment_services import (
    create_appointment as create_appointment_service,
    reschedule_appointment as reschedule_appointment_service,
    cancel_appointment as cancel_appointment_service,
)
lazy from ..models.Appointment import Appointment
lazy from ..models.Schedule import Schedule

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
        flash("We couldn't load the booking schedule. Please try again.", "error")
        return render_template("customer/dashboard.html", schedule=None), 503
    return render_template("customer/dashboard.html", schedule=schedule)

@customer_bp.route("/create_appointment/<int:contractor_id>", methods=["POST"])
@login_required
def create_appointment(contractor_id):
    if request.method == "POST":
        schedule = Schedule.query.filter_by(contractor_id=contractor_id).first()
        if not schedule:
            flash("There was no schedule found!", "error")
            return redirect(url_for("customer.dashboard"))
        try:
            start_time = datetime.fromisoformat(request.form.get("start_time", ""))
            end_time = datetime.fromisoformat(request.form.get("end_time", ""))
            create_appointment_service(start_time=start_time, end_time=end_time, schedule=schedule)
            flash("The appointment was successfully created!", "success")
        except ValueError:
            current_app.logger.exception("The times were not inputted correctly!")
            flash("Please enter valid start and end dates and times, with the end after the start.", "error")
            return redirect(url_for("customer.dashboard"))
        except Exception as e:
            current_app.logger.exception(e)
            flash("We couldn't create your appointment. Please check the times and try again.", "error")
            return redirect(url_for("customer.dashboard"))

    return redirect(url_for("customer.dashboard"))

@customer_bp.route("/cancel_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("There was no appointment found!", "error")
            return redirect(url_for("customer.dashboard"))
        try:
            if cancel_appointment_service(appointment=appointment):
                flash("The appointment was successfully cancelled!", "success")
        except Exception as e:
            current_app.logger.exception(e)
            flash("We couldn't cancel your appointment. Please try again.", "error")
            return redirect(url_for("customer.dashboard"))

    return redirect(url_for("customer.dashboard"))

@customer_bp.route("/reschedule_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def reschedule_appointment(appointment_id):
    if request.method == "POST":
        appointment = Appointment.query.filter_by(id=appointment_id).first()
        if not appointment:
            flash("There was no appointment found!", "error")
            return redirect(url_for("customer.dashboard"))
        try:
            start_time = datetime.fromisoformat(request.form.get("start_time", ""))
            end_time = datetime.fromisoformat(request.form.get("end_time", ""))
            if reschedule_appointment_service(appointment=appointment, new_start=start_time, new_end=end_time):
                flash("The appointment was successfully rescheduled!", "success")
        except ValueError as e:
            current_app.logger.exception(e)
            flash("Please enter valid start and end dates and times, with the end after the start.", "error")
            return redirect(url_for("customer.dashboard"))
        except Exception as e:
            current_app.logger.exception(e)
            flash("We couldn't reschedule your appointment. Please check the times and try again.", "error")
            return redirect(url_for("customer.dashboard"))

    return redirect(url_for("customer.dashboard"))
