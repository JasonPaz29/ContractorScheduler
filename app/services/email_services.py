lazy from itsdangerous import URLSafeSerializer
lazy from flask import current_app, url_for
lazy from ..models.Appointment import Appointment, Status
lazy from ..models.Contractor import Contractor
lazy from ..models.Schedule import Schedule
lazy from flask_mail import Message
lazy from ..extensions import db, mail
lazy from ..models.Customer import Customer

def generate_email_token(email: str) -> str:
    serializer = URLSafeSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="email")


def _schedule_url(appointment: Appointment, recipient: Customer | Contractor, *, show_appointment: bool = True) -> str:
    role = "contractor" if isinstance(recipient, Contractor) else "customer"
    if show_appointment and appointment.id is not None:
        anchor = f"{role}-appointment-{appointment.id}"
    else:
        anchor = "booking-calendar" if role == "contractor" else "your-appointments"
    return url_for(f"{role}.dashboard", _external=True, _anchor=anchor)


def _send_email(recipient: Customer | Contractor, subject: str, body: str, event: str) -> tuple[bool, str]:
    try:
        message = Message(subject=subject, recipients=[recipient.email], body=body)
        mail.send(message)
    except Exception:
        current_app.logger.exception("The %s email could not be sent", event)
        return False, f"The {event} email could not be sent!"
    return True, f"The {event} email was successfully sent!"


def send_new_request_email(appointment: Appointment) -> tuple[bool, str]:
    if not current_app.config["MAIL_SERVER"]:
        return False, "The mail server is not configured yet!"
    #Needed to get contractor
    schedule = db.session.get(Schedule, appointment.schedule_id)
    if schedule is None:
        return False, "The appointment's schedule could not found!"
    contractor = db.session.get(Contractor, schedule.contractor_id)
    if contractor is None:
        return False, "The schedule's contractor could not be found!"

    schedule_url = url_for(
        "contractor.dashboard",
        _external=True,
        _anchor=f"contractor-appointment-{appointment.id}" if appointment.id is not None else "pending-heading",
    )
    customer_name = appointment.customer.display_name if appointment.customer is not None else "A customer"

    subject = "New appointment request | IT Scheduler"
    body = (
        f"Hi {contractor.display_name},\n\n"
        f"{customer_name} has requested an appointment.\n\n"
        f"Requested start: {appointment.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"Requested end: {appointment.end_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
        "This request is awaiting your reply and has not been confirmed yet.\n\n"
        "Review the request in your schedule:\n"
        f"{schedule_url}\n\n"
        "Sign in to your contractor account if prompted. From your schedule, "
        "you can confirm, decline, or reschedule the request.\n\n"
        "Thank you,\n"
        "IT Scheduler"
    )
    message = Message(subject=subject, recipients=[contractor.email], body=body)

    try:
        mail.send(message)
    except Exception as e:
        current_app.logger.exception("The new request email could not be sent")
        return False, "The email failed to send!"

    return True, "The request email was successfully sent!"


def send_confirmation_email(appointment: Appointment) -> tuple[bool, str]:
    if not current_app.config.get("MAIL_SERVER"):
        return False, "The mail server is not configured yet!"

    customer = db.session.get(Customer, appointment.customer_id)
    if not customer:
        return False, "There was no customer found!"

    schedule_url = _schedule_url(appointment, customer)
    subject = "Your appointment is confirmed | IT Scheduler"

    body = (
        f"Hi {customer.display_name},\n\n"
        "Your appointment has been confirmed. You're all set for the following times:\n\n"
        f"Start: {appointment.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"End: {appointment.end_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
        "View your appointment in your schedule:\n"
        f"{schedule_url}\n\n"
        "Sign in to your customer account if prompted. If your plans change, "
        "you can reschedule or cancel from your appointment details.\n\n"
        "Thank you,\n"
        "IT Scheduler"
    )
    return _send_email(customer, subject, body, "confirmation")


def send_rejection_email(appointment: Appointment) -> tuple[bool, str]:
    if not current_app.config.get("MAIL_SERVER"):
        return False, "The mail server is not configured yet!"

    customer = db.session.get(Customer, appointment.customer_id)
    if customer is None:
        return False, "There was no customer found!"

    schedule_url = _schedule_url(appointment, customer)
    subject = "An update on your appointment request | IT Scheduler"
    body = (
        f"Hi {customer.display_name},\n\n"
        "Your contractor wasn't able to accept your appointment request for these times:\n\n"
        f"Requested start: {appointment.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"Requested end: {appointment.end_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
        "This request is marked as Not accepted, and no appointment has been confirmed for it. "
        "You can check booked times and request another appointment from your schedule:\n"
        f"{schedule_url}\n\n"
        "Sign in to your customer account if prompted.\n\n"
        "Thank you,\n"
        "IT Scheduler"
    )
    return _send_email(customer, subject, body, "rejection")


def send_cancellation_email(appointment: Appointment, recipient: Customer | Contractor) -> tuple[bool, str]:
    if not current_app.config.get("MAIL_SERVER"):
        return False, "The mail server is not configured yet!"

    is_contractor = isinstance(recipient, Contractor)
    # Canceled appointments have no row in the contractor's active appointment lists.
    schedule_url = _schedule_url(appointment, recipient, show_appointment=not is_contractor)
    customer_name = appointment.customer.display_name if appointment.customer is not None else "a customer"
    introduction = (
        f"An appointment with {customer_name} has been canceled."
        if is_contractor else "Your appointment has been canceled."
    )
    next_step = (
        "The appointment is no longer active. Check your calendar for the latest schedule."
        if is_contractor else
        "The appointment is marked as Canceled. If you still need an appointment, "
        "you can check booked times and send a new request."
    )
    subject = "Appointment canceled | IT Scheduler"
    body = (
        f"Hi {recipient.display_name},\n\n"
        f"{introduction}\n\n"
        f"Canceled start: {appointment.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"Canceled end: {appointment.end_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
        f"{next_step}\n\n"
        "View your schedule:\n"
        f"{schedule_url}\n\n"
        f"Sign in to your {'contractor' if is_contractor else 'customer'} account if prompted.\n\n"
        "Thank you,\n"
        "IT Scheduler"
    )
    return _send_email(recipient, subject, body, "cancellation")


def send_reschedule_email(appointment: Appointment, recipient: Customer | Contractor) -> tuple[bool, str]:
    if not current_app.config.get("MAIL_SERVER"):
        return False, "The mail server is not configured yet!"

    if appointment.status not in (Status.PENDING, Status.ACCEPETED):
        return False, "Only pending or confirmed appointments can have reschedule notifications."

    is_contractor = isinstance(recipient, Contractor)
    schedule_url = _schedule_url(appointment, recipient)
    customer_name = appointment.customer.display_name if appointment.customer is not None else "a customer"
    introduction = (
        f"An appointment with {customer_name} has been rescheduled."
        if is_contractor else "Your appointment has been rescheduled."
    )
    if appointment.status == Status.ACCEPETED:
        status_message = "The appointment remains confirmed at the new times."
    elif is_contractor:
        status_message = "This request is still awaiting your reply. Review the new times before confirming it."
    else:
        status_message = "Your request is still awaiting the contractor's confirmation."

    subject = "Appointment rescheduled | IT Scheduler"
    body = (
        f"Hi {recipient.display_name},\n\n"
        f"{introduction} Here are the updated times:\n\n"
        f"New start: {appointment.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"New end: {appointment.end_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n"
        f"{status_message}\n\n"
        "View the updated appointment in your schedule:\n"
        f"{schedule_url}\n\n"
        f"Sign in to your {'contractor' if is_contractor else 'customer'} account if prompted.\n\n"
        "Thank you,\n"
        "IT Scheduler"
    )
    return _send_email(recipient, subject, body, "reschedule")
