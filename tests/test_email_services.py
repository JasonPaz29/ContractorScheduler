import unittest
from urllib.parse import urlsplit
from unittest.mock import patch

from flask import render_template
from flask_login import login_user

from app.extensions import db
from app.models.Appointment import Appointment, Status
from app.models.Schedule import Schedule
from app.services.email_services import (
    send_confirmation_email,
    send_rejection_email,
    send_cancellation_email,
    send_reschedule_email,
)
from tests.test_frontend import make_frontend_test_app


class EmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = make_frontend_test_app()
        self.app.config["MAIL_SERVER"] = "smtp.example.com"
        self.context = self.app.test_request_context("/", base_url="https://scheduler.example.com")
        self.context.push()
        self.schedule = Schedule.query.one()
        self.contractor = self.schedule.contractor
        self.appointment = Appointment.query.filter_by(status=Status.PENDING).first()
        self.customer = self.appointment.customer
        # All delivery is intercepted, regardless of any local SMTP configuration.
        self.delivery_patch = patch("app.services.email_services.mail.send")
        self.delivery = self.delivery_patch.start()

    def tearDown(self):
        self.delivery_patch.stop()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def sent_message(self, result, recipient, role, anchor):
        self.assertTrue(result[0], result)
        self.delivery.assert_called_once()
        message = self.delivery.call_args.args[0]
        self.assertEqual(message.recipients, [recipient.email])
        self.assertIn(recipient.display_name, message.body)
        self.assertIn(self.appointment.start_time.strftime("%A, %B %d, %Y at %I:%M %p"), message.body)
        self.assertIn(self.appointment.end_time.strftime("%A, %B %d, %Y at %I:%M %p"), message.body)
        self.assertNotIn("CODEX IMPLEMENT", message.subject + message.body)
        self.assertNotIn("PLACEHOLDER", message.subject + message.body)
        url = urlsplit(next(line for line in message.body.splitlines() if line.startswith("https://")))
        self.assertEqual((url.scheme, url.netloc, url.path, url.fragment),
                         ("https", "scheduler.example.com", f"/{role}/dashboard", anchor))
        return message

    def test_confirmation_goes_to_customer_with_confirmed_details(self):
        self.appointment.status = Status.ACCEPETED
        db.session.commit()
        message = self.sent_message(send_confirmation_email(self.appointment), self.customer,
                                    "customer", f"customer-appointment-{self.appointment.id}")
        self.assertIn("Your appointment has been confirmed", message.body)

    def test_rejection_goes_to_customer_with_next_action(self):
        self.appointment.status = Status.REJECTED
        db.session.commit()
        message = self.sent_message(send_rejection_email(self.appointment), self.customer,
                                    "customer", f"customer-appointment-{self.appointment.id}")
        self.assertIn("Not accepted", message.body)
        self.assertIn("request another appointment", message.body)
        login_user(self.customer)
        html = render_template("customer/dashboard.html", schedule=self.schedule)
        self.assertIn(f'id="customer-appointment-{self.appointment.id}"', html)

    def test_cancellation_links_to_visible_content_for_both_roles(self):
        self.appointment.status = Status.CANCELED
        db.session.commit()
        for recipient, role, anchor in (
            (self.customer, "customer", f"customer-appointment-{self.appointment.id}"),
            (self.contractor, "contractor", "booking-calendar"),
        ):
            with self.subTest(role=role):
                self.delivery.reset_mock()
                message = self.sent_message(send_cancellation_email(self.appointment, recipient),
                                            recipient, role, anchor)
                self.assertIn("canceled", message.body)
                login_user(recipient)
                html = render_template(f"{role}/dashboard.html", schedule=self.schedule)
                self.assertIn(f'id="{anchor}"', html)
                if role == "contractor":
                    self.assertNotIn(f'id="contractor-appointment-{self.appointment.id}"', html)
                    self.assertIn(self.customer.display_name, message.body)

    def test_reschedule_preserves_pending_or_confirmed_wording_for_both_roles(self):
        for status in (Status.PENDING, Status.ACCEPETED):
            self.appointment.status = status
            db.session.commit()
            for recipient, role in ((self.customer, "customer"), (self.contractor, "contractor")):
                with self.subTest(status=status, role=role):
                    self.delivery.reset_mock()
                    message = self.sent_message(send_reschedule_email(self.appointment, recipient),
                                                recipient, role, f"{role}-appointment-{self.appointment.id}")
                    self.assertIn("New start:", message.body)
                    self.assertIn("New end:", message.body)
                    if status == Status.PENDING:
                        self.assertIn("still awaiting", message.body)
                        self.assertNotIn("remains confirmed", message.body)
                    else:
                        self.assertIn("remains confirmed", message.body)

    def test_closed_appointments_do_not_send_reschedule_notifications(self):
        for status in (Status.CANCELED, Status.REJECTED):
            self.appointment.status = status
            self.assertFalse(send_reschedule_email(self.appointment, self.customer)[0])
        self.delivery.assert_not_called()

    def test_missing_customer_stops_confirmation_and_rejection(self):
        appointment = Appointment()
        appointment.customer_id = 999999
        for sender in (send_confirmation_email, send_rejection_email):
            self.assertFalse(sender(appointment)[0])
        self.delivery.assert_not_called()

    def test_unconfigured_server_does_not_attempt_delivery(self):
        self.app.config["MAIL_SERVER"] = None
        for sender, args in (
            (send_confirmation_email, (self.appointment,)),
            (send_rejection_email, (self.appointment,)),
            (send_cancellation_email, (self.appointment, self.contractor)),
            (send_reschedule_email, (self.appointment, self.customer)),
        ):
            self.assertFalse(sender(*args)[0])
        self.delivery.assert_not_called()

    def test_delivery_failure_returns_false_and_keeps_saved_appointment(self):
        self.delivery.side_effect = RuntimeError("Synthetic SMTP failure")
        original = (self.appointment.status, self.appointment.start_time, self.appointment.end_time)
        for sender, args in (
            (send_confirmation_email, (self.appointment,)),
            (send_rejection_email, (self.appointment,)),
            (send_cancellation_email, (self.appointment, self.contractor)),
            (send_reschedule_email, (self.appointment, self.customer)),
        ):
            with self.subTest(sender=sender.__name__):
                with self.assertLogs(self.app.logger, level="ERROR"):
                    self.assertFalse(sender(*args)[0])
                db.session.expire(self.appointment)
                self.assertEqual((self.appointment.status, self.appointment.start_time, self.appointment.end_time), original)


if __name__ == "__main__":
    unittest.main()
