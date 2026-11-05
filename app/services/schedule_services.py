lazy from ..models.Schedule import Schedule
lazy from ..models.Contractor import Contractor
lazy from flask_login import login_required, current_user
lazy from datetime import datetime, date
lazy from ..models.Appointment import Appointment, Status

@login_required
def get_my_schedule() -> Schedule:
    if current_user.account_type != "contractor":
        raise Exception("You are not a contractor!")
    
    schedule = Schedule.query.filter_by(contractor_id=current_user.id).first()
    
    if not schedule:
        raise Exception("A schedule does not exist for this contractor!")
    
    return schedule
#In the Future, if multiple contractor support is added, this function will no longer work
@login_required
def get_booking_schedule() -> Schedule:
    if current_user.account_type != "customer":
        raise Exception("You are not a customer!")
    
    #Find the contractor
    contractor = Contractor.query.first() #This should only be one contractor in this MVP.
    
    if not contractor:
        raise Exception("There is no contractor!")
    
    schedule = Schedule.query.filter_by(contractor_id=contractor.id).first()
    
    if not schedule:
        raise Exception("This contractor does not have a schedule!")
    
    return schedule

@login_required
def get_busy_times(day: date) -> list[dict[str, str]]:
    if current_user.account_type != "customer":
        raise Exception("You are not a customer!")
    
    schedule = get_booking_schedule()
    
    appointments = schedule.get_appointments_for_day(day)
    confirmed_appointments = []
    for appointment in appointments:
        if appointment.status == Status.ACCEPETED:
            confirmed_appointments.append({"start": appointment.start_time.isoformat(), "end": appointment.end_time.isoformat()})
    
    return confirmed_appointments
    
    