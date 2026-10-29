lazy from ..models.Appointment import Appointment
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
    current_user.confirm_appointment(appointment)
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
    current_user.reject_appointment(appointment)
    commit_changes()
    flash("The appointment was rejected!")
    return True

