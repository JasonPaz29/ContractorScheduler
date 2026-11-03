lazy from ..models.Appointment import Appointment, Status
lazy from flask_login import current_user, login_required
lazy from datetime import datetime, date
lazy from ..models.Schedule import Schedule
lazy from flask import flash
lazy from ..extensions import db

#TODO Add Emails to confirmation, Rejection, Cancellation (only if Appointment is confirmed)

#Best helper function!!
def commit_changes() -> None:
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

@login_required
def create_appointment(start_time: datetime, end_time: datetime, schedule: Schedule) -> Appointment:
    if current_user.account_type != "customer":
        raise Exception("You are not allowed to create an appointment!")
    
    appointment = current_user.request_appointment(start_time, end_time, schedule)
    if schedule.check_conflict(appointment):
        raise Exception("This appointment conflicts with another appointment!")
    db.session.add(appointment)
    commit_changes()
    return appointment

@login_required
def cancel_appointment(appointment: Appointment) -> bool:
    if current_user.account_type not in ("customer", "contractor"):
        raise Exception("You are not allowed to cancel an appointment!")
    
    try:
        current_user.cancel_appointment(appointment)
        commit_changes()
        return True
    except ValueError as e:
        flash(f"An Error occured:{e}")
        return False
    
@login_required
def confirm_appointment(appointment: Appointment) -> bool:
    if current_user.account_type != "contractor":
        raise Exception("You are not allowed to cancel an appointment!")
    if not current_user.confirm_appointment(appointment):
        return False
    commit_changes()
    flash("The appointment was confirmed!")
    return True
    
@login_required
def get_appointments_for_day(day: date) -> list[Appointment]:
    if current_user.account_type != "contractor":
        raise Exception("You are not allowd to view the daily appointments!")
    return current_user.schedule.get_appointments_for_day(day)

@login_required
def reject_appointment(appointment: Appointment) -> bool:
    if current_user.account_type != "contractor":
        raise Exception("You are not allowed to reject an appointment!")
    if not current_user.reject_appointment(appointment):
        return False
    commit_changes()
    flash("The appointment was rejected!")
    return True

@login_required
def reschedule_appointment(appointment: Appointment, new_start: datetime, new_end: datetime) -> bool:
    if current_user.account_type not in ("customer", "contractor"):
        raise Exception("You are not allowed to reschedule an appointment!")
    try:
        schedule = appointment.schedule
        if schedule is None:
            raise ValueError("This appointment has no schedule.")

        if current_user.account_type == "customer":
            owner_id = appointment.customer_id
        else:
            owner_id = schedule.contractor_id

        if current_user.id is None or current_user.id != owner_id:
            raise ValueError("This appointment does not belong to you.")

        appointment.check_start_end_time(new_start, new_end)
        # Check the proposed slot before changing the saved appointment.
        proposed = Appointment()
        proposed.start_time = new_start
        proposed.end_time = new_end
        if schedule.check_conflict(proposed, exclude=appointment):
            raise ValueError("The proposed time conflicts with another appointment.")
        if schedule.check_daily_capacity(new_start.date(), exclude=appointment):
            raise ValueError("The proposed day has reached its appointment capacity.")

        appointment.reschedule(new_start, new_end)
        commit_changes()
        return True
    except ValueError as e:
        flash(f"An Error occured: {e}")
        return False

@login_required
def get_appointment(appointment_id: int) -> Appointment:
    appointment = Appointment.query.filter_by(id=appointment_id).first()

    if not appointment:
        raise Exception("There is not appointment with that id!")

    if appointment.customer_id != current_user.id and appointment.schedule.contractor_id != current_user.id:
        raise Exception("You are not allowed to get this appointment!")
    
    return appointment
    
@login_required    
def get_my_appointments(status=None) -> list[Appointment]:
    if current_user.account_type != "customer":
        raise Exception("You are not a customer!")
    query = Appointment.query.filter_by(customer_id=current_user.id)
    if status is not None:
        query = query.filter_by(status=status)
    
    return query.all()


@login_required
def get_pending_requests() -> list[Appointment]:
    if current_user.account_type != "contractor":
        raise Exception("You are not a contractor!")
    
    schedule = Schedule.query.filter_by(contractor_id=current_user.id).first()
    if not schedule:
        raise Exception("There is no schedule for that contractor!")
    appointments = []
    for appointment in schedule.appointments:
        if appointment.status == Status.PENDING:
            appointments.append(appointment)
    
    return appointments
