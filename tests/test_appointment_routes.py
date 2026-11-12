import unittest
from datetime import datetime, timedelta
from html.parser import HTMLParser

from app.extensions import db
from app.models.Appointment import Appointment, Status
from app.models.Contractor import Contractor
from app.models.Schedule import Schedule
from app.models.User import User
from tests.test_frontend import make_frontend_test_app, PREVIEW_PASSWORD


class FormParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            self.forms.append(dict(attrs))


class AppointmentRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = make_frontend_test_app()
        self.previous_logger_disabled = self.app.logger.disabled
        self.app.logger.disabled = True
        self.customer = self.app.test_client()
        self.contractor = self.app.test_client()
        self.login(self.customer, "alex")
        self.login(self.contractor, "sam")
        self.start = (datetime.now() + timedelta(days=10)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        with self.app.app_context():
            self.contractor_id = Schedule.query.one().contractor_id
            self.customer_id = User.query.filter_by(username="alex").one().id

    def tearDown(self):
        self.app.logger.disabled = self.previous_logger_disabled
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login(self, client, username):
        client.get("/auth/logout")
        client.post("/auth/login", data={"identifier": username, "password": PREVIEW_PASSWORD})

    def times(self, start=None, end=None):
        start = start or self.start
        end = end or start + timedelta(hours=1)
        return {"start_time": start.isoformat(timespec="minutes"), "end_time": end.isoformat(timespec="minutes")}

    def snapshot(self, appointment_id):
        with self.app.app_context():
            appointment = db.session.get(Appointment, appointment_id)
            return appointment.status, appointment.start_time, appointment.end_time

    def post(self, client, path, data=None):
        with client.session_transaction() as session:
            session.pop("_flashes", None)
        response = client.post(path, data=data or {})
        self.assertEqual(response.status_code, 302)
        with client.session_transaction() as session:
            messages = session.get("_flashes", [])
        self.assertEqual(len(messages), 1, messages)
        return messages[0]

    def new_request(self):
        category, _ = self.post(self.customer, f"/customer/create_appointment/{self.contractor_id}", self.times())
        self.assertEqual(category, "success")
        with self.app.app_context():
            return Appointment.query.filter_by(customer_id=self.customer_id, start_time=self.start, status=Status.PENDING).one().id

    def form_action(self, client, dashboard, suffix):
        html = client.get(dashboard).get_data(as_text=True)
        actions = [form["action"] for form in FormParser(html).forms if form.get("action", "").endswith(suffix)]
        self.assertEqual(len(actions), 1, actions)
        return actions[0]

    def test_rendered_forms_complete_request_confirm_reschedule_cancel_flow(self):
        create = self.form_action(self.customer, "/customer/dashboard", f"create_appointment/{self.contractor_id}")
        self.assertEqual(self.post(self.customer, create, self.times())[0], "success")
        with self.app.app_context():
            appointment_id = Appointment.query.filter_by(customer_id=self.customer_id, start_time=self.start).one().id
        self.assertEqual(self.snapshot(appointment_id)[0], Status.PENDING)
        confirm = self.form_action(self.contractor, "/contractor/dashboard", f"confirm_appointment/{appointment_id}")
        self.assertEqual(self.post(self.contractor, confirm)[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[0], Status.ACCEPETED)
        reschedule = self.form_action(self.customer, "/customer/dashboard", f"reschedule_appointment/{appointment_id}")
        new_start = self.start + timedelta(hours=2)
        self.assertEqual(self.post(self.customer, reschedule, self.times(new_start))[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[1], new_start)
        cancel = self.form_action(self.contractor, "/contractor/dashboard", f"cancel_appointment/{appointment_id}")
        self.assertEqual(self.post(self.contractor, cancel)[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[0], Status.CANCELED)
        html = self.customer.get("/customer/dashboard").get_data(as_text=True)
        self.assertNotIn(f"reschedule_appointment/{appointment_id}\"", html)
        self.assertNotIn(f"cancel_appointment/{appointment_id}\"", html)

    def test_rendered_decline_form_and_customer_cancellation(self):
        appointment_id = self.new_request()
        reject = self.form_action(self.contractor, "/contractor/dashboard", f"reject_appointment/{appointment_id}")
        self.assertEqual(self.post(self.contractor, reject)[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[0], Status.REJECTED)
        appointment_id = self.new_request()
        cancel = self.form_action(self.customer, "/customer/dashboard", f"cancel_appointment/{appointment_id}")
        self.assertEqual(self.post(self.customer, cancel)[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[0], Status.CANCELED)
        self.assertEqual(self.post(self.customer, cancel)[0], "error")

    def test_conflicting_customer_reschedule_has_one_error_and_keeps_times(self):
        appointment_id = self.new_request()
        original = self.snapshot(appointment_id)
        with self.app.app_context():
            booked = Appointment.query.filter_by(status=Status.ACCEPETED).first()
            proposed = self.times(booked.start_time, booked.end_time)
        category, _ = self.post(self.customer, f"/customer/reschedule_appointment/{appointment_id}", proposed)
        self.assertEqual(category, "error")
        self.assertEqual(self.snapshot(appointment_id), original)

    def test_capacity_failure_keeps_request_pending_then_contractor_can_reschedule(self):
        appointment_id = self.new_request()
        with self.app.app_context():
            schedule = Schedule.query.one()
            schedule.max_daily_appointments = 1
            customer = db.session.get(User, self.customer_id)
            booked = customer.request_appointment(self.start + timedelta(hours=2), self.start + timedelta(hours=3), schedule)
            booked.status = Status.ACCEPETED
            db.session.add(booked)
            db.session.commit()
        self.assertEqual(self.post(self.contractor, f"/contractor/confirm_appointment/{appointment_id}")[0], "error")
        self.assertEqual(self.snapshot(appointment_id)[0], Status.PENDING)
        new_start = self.start + timedelta(days=1)
        path = self.form_action(self.contractor, "/contractor/dashboard", f"reschedule_appointment/{appointment_id}")
        self.assertEqual(self.post(self.contractor, path, self.times(new_start))[0], "success")
        self.assertEqual(self.snapshot(appointment_id)[1], new_start)

    def test_bad_datetime_and_reversed_interval_show_errors_without_changes(self):
        appointment_id = self.new_request()
        original = self.snapshot(appointment_id)
        for client, role in ((self.customer, "customer"), (self.contractor, "contractor")):
            for data in ({}, {"start_time": "bad", "end_time": "bad"}, self.times(self.start, self.start - timedelta(hours=1))):
                with self.subTest(role=role, data=data):
                    self.assertEqual(self.post(client, f"/{role}/reschedule_appointment/{appointment_id}", data)[0], "error")
                    self.assertEqual(self.snapshot(appointment_id), original)

    def test_closed_appointment_cannot_be_rescheduled_by_either_role(self):
        appointment_id = self.new_request()
        self.post(self.contractor, f"/contractor/reject_appointment/{appointment_id}")
        original = self.snapshot(appointment_id)
        for client, role in ((self.customer, "customer"), (self.contractor, "contractor")):
            self.assertEqual(self.post(client, f"/{role}/reschedule_appointment/{appointment_id}", self.times(self.start + timedelta(days=1)))[0], "error")
            self.assertEqual(self.snapshot(appointment_id), original)

    def test_other_users_cannot_change_appointment(self):
        appointment_id = self.new_request()
        original = self.snapshot(appointment_id)
        self.login(self.customer, "robin")
        for action in ("cancel", "reschedule"):
            self.assertEqual(self.post(self.customer, f"/customer/{action}_appointment/{appointment_id}", self.times())[0], "error")
            self.assertEqual(self.snapshot(appointment_id), original)
        with self.app.app_context():
            other = Contractor("Other Contractor", "other_contractor", "other_contractor@example.com", PREVIEW_PASSWORD)
            db.session.add(Schedule(contractor=other))
            db.session.commit()
        self.login(self.contractor, "other_contractor")
        for action in ("confirm", "reject", "cancel", "reschedule"):
            self.assertEqual(self.post(self.contractor, f"/contractor/{action}_appointment/{appointment_id}", self.times())[0], "error")
            self.assertEqual(self.snapshot(appointment_id), original)

    def test_signed_out_actions_require_login_and_get_cannot_mutate(self):
        appointment_id = self.new_request()
        original = self.snapshot(appointment_id)
        anonymous = self.app.test_client()
        for role, actions in (("customer", ("cancel", "reschedule")), ("contractor", ("confirm", "reject", "cancel", "reschedule"))):
            for action in actions:
                path = f"/{role}/{action}_appointment/{appointment_id}"
                self.assertIn("/auth/login", anonymous.post(path).location)
                self.assertEqual(anonymous.get(path).status_code, 405)
        self.assertEqual(self.snapshot(appointment_id), original)


if __name__ == "__main__":
    unittest.main()
