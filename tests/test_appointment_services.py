import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import Flask, get_flashed_messages
from flask_login import login_user

from app.extensions import db, login_manager
from app.models.Customer import Customer
from app.models.Contractor import Contractor
from app.models.Appointment import Appointment, Status
from app.models.Schedule import Schedule
from app.services.appointment_services import (
    confirm_appointment,
    reject_appointment,
    reschedule_appointment,
)


class AppointmentServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="appointment-service-tests-only",
            SQLALCHEMY_DATABASE_URI="sqlite://",
        )
        db.init_app(self.app)
        login_manager.init_app(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.customer = Customer("Customer", "test_customer", "test_customer@example.com", "test_password")
        self.other_customer = Customer("Other", "other_customer", "other_customer@example.com", "test_password")
        self.contractor = Contractor("Contractor", "test_contractor", "test_contractor@example.com", "test_password")
        self.other_contractor = Contractor("Other", "other_contractor", "other_contractor@example.com", "test_password")
        self.schedule = Schedule(contractor=self.contractor, max_daily_appointments=6)
        self.other_schedule = Schedule(contractor=self.other_contractor)
        db.session.add_all([
            self.customer,
            self.other_customer,
            self.contractor,
            self.other_contractor,
            self.schedule,
            self.other_schedule,
        ])
        db.session.commit()
        self.start = (datetime.now() + timedelta(days=2)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def make_appointment(self, start=None, status=Status.ACCEPETED):
        start = self.start if start is None else start
        appointment = self.customer.request_appointment(
            start, start + timedelta(hours=1), self.schedule
        )
        appointment.status = status
        db.session.add(appointment)
        db.session.commit()
        return appointment

    def assert_times_unchanged(self, appointment, original):
        self.assertEqual((appointment.start_time, appointment.end_time), original)
        db.session.expire(appointment)
        self.assertEqual((appointment.start_time, appointment.end_time), original)

    def test_confirmation_persists_accepted_status(self):
        appointment = self.make_appointment(status=Status.PENDING)
        with self.app.test_request_context("/"):
            login_user(self.contractor)
            self.assertTrue(confirm_appointment(appointment))
            self.assertIn("The appointment was confirmed!", get_flashed_messages())
        db.session.expire(appointment)
        self.assertEqual(appointment.status, Status.ACCEPETED)

    def test_rejection_persists_rejected_status(self):
        appointment = self.make_appointment(status=Status.PENDING)
        with self.app.test_request_context("/"):
            login_user(self.contractor)
            self.assertTrue(reject_appointment(appointment))
            self.assertIn("The appointment was rejected!", get_flashed_messages())
        db.session.expire(appointment)
        self.assertEqual(appointment.status, Status.REJECTED)

    def test_unavailable_confirmation_stays_pending_without_success_message(self):
        self.schedule.max_daily_appointments = 1
        self.make_appointment()
        appointment = self.make_appointment(
            self.start + timedelta(hours=2), status=Status.PENDING
        )
        with self.app.test_request_context("/"):
            login_user(self.contractor)
            self.assertFalse(confirm_appointment(appointment))
            self.assertEqual(get_flashed_messages(), [])
        db.session.expire(appointment)
        self.assertEqual(appointment.status, Status.PENDING)

    def test_customer_can_move_own_appointment_without_self_conflict(self):
        self.schedule.max_daily_appointments = 1
        appointment = self.make_appointment()
        new_start = self.start + timedelta(minutes=30)
        new_end = new_start + timedelta(hours=1)
        with self.app.test_request_context("/"):
            login_user(self.customer)
            self.assertTrue(reschedule_appointment(appointment, new_start, new_end))
        db.session.expire(appointment)
        self.assertEqual((appointment.start_time, appointment.end_time), (new_start, new_end))

    def test_contractor_can_move_appointment_to_an_empty_day(self):
        self.schedule.max_daily_appointments = 1
        appointment = self.make_appointment()
        new_start = self.start + timedelta(days=1)
        new_end = new_start + timedelta(hours=1)
        with self.app.test_request_context("/"):
            login_user(self.contractor)
            self.assertTrue(reschedule_appointment(appointment, new_start, new_end))
        db.session.expire(appointment)
        self.assertEqual((appointment.start_time, appointment.end_time), (new_start, new_end))

    def test_other_customer_and_contractor_cannot_reschedule(self):
        appointment = self.make_appointment()
        original = (appointment.start_time, appointment.end_time)
        for user in (self.other_customer, self.other_contractor):
            with self.subTest(account_type=user.account_type):
                with self.app.test_request_context("/"):
                    login_user(user)
                    self.assertFalse(reschedule_appointment(
                        appointment, self.start + timedelta(hours=3), self.start + timedelta(hours=4)
                    ))
                    self.assertTrue(get_flashed_messages())
                self.assert_times_unchanged(appointment, original)

    def test_overlapping_reschedule_preserves_original_times(self):
        appointment = self.make_appointment()
        self.make_appointment(self.start + timedelta(hours=2))
        original = (appointment.start_time, appointment.end_time)
        for user in (self.customer, self.contractor):
            with self.subTest(account_type=user.account_type):
                with self.app.test_request_context("/"):
                    login_user(user)
                    self.assertFalse(reschedule_appointment(
                        appointment,
                        self.start + timedelta(hours=2, minutes=30),
                        self.start + timedelta(hours=3, minutes=30),
                    ))
                self.assert_times_unchanged(appointment, original)

    def test_full_target_day_preserves_original_times(self):
        self.schedule.max_daily_appointments = 1
        appointment = self.make_appointment()
        target = self.start + timedelta(days=1)
        self.make_appointment(target)
        original = (appointment.start_time, appointment.end_time)
        with self.app.test_request_context("/"):
            login_user(self.contractor)
            self.assertFalse(reschedule_appointment(
                appointment, target + timedelta(hours=3), target + timedelta(hours=4)
            ))
        self.assert_times_unchanged(appointment, original)

    def test_invalid_interval_preserves_original_times(self):
        appointment = self.make_appointment()
        original = (appointment.start_time, appointment.end_time)
        with self.app.test_request_context("/"):
            login_user(self.customer)
            self.assertFalse(reschedule_appointment(appointment, self.start, self.start))
        self.assert_times_unchanged(appointment, original)

    def test_commit_failure_rolls_back_reschedule(self):
        appointment = self.make_appointment()
        original = (appointment.start_time, appointment.end_time)
        with self.app.test_request_context("/"):
            login_user(self.customer)
            with patch.object(db.session, "commit", side_effect=RuntimeError("database unavailable")):
                with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                    reschedule_appointment(
                        appointment, self.start + timedelta(hours=3), self.start + timedelta(hours=4)
                    )
        self.assert_times_unchanged(appointment, original)


if __name__ == "__main__":
    unittest.main()
