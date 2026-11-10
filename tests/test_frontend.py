import ast
import logging
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.User import User
from app.models.Customer import Customer
from app.models.Contractor import Contractor
from app.models.Schedule import Schedule
from app.models.Appointment import Appointment, Status


PREVIEW_PASSWORD = "preview-password-only"


def make_frontend_test_app():
    """Use a separate, in-memory database; never read or write the real app DB."""
    with patch.object(Config, "SQLALCHEMY_DATABASE_URI", "sqlite://"):
        app = create_app()
    app.config.update(
        TESTING=True, SECRET_KEY="frontend-tests-only", TEMPLATES_AUTO_RELOAD=True
    )
    with app.app_context():
        db.create_all()
        customer = Customer("Alex Morgan", "alex", PREVIEW_PASSWORD)
        contractor = Contractor("Sam Taylor", "sam", PREVIEW_PASSWORD)
        other_customer = Customer("Nina Patel", "private_customer", PREVIEW_PASSWORD)
        empty_customer = Customer("Robin Lee", "robin", PREVIEW_PASSWORD)
        schedule = Schedule(contractor=contractor)
        db.session.add_all([customer, contractor, other_customer, empty_customer, schedule])
        db.session.flush()
        start = (datetime.now() + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        for owner, offset, status in [
            (other_customer, 0, Status.ACCEPETED),
            (customer, 2, Status.ACCEPETED),
            (customer, 5, Status.PENDING),
            (other_customer, 28, Status.PENDING),
            (customer, 50, Status.REJECTED),
            (customer, 74, Status.CANCELED),
        ]:
            appointment = owner.request_appointment(
                start + timedelta(hours=offset),
                start + timedelta(hours=offset + 1),
                schedule,
            )
            appointment.status = status
            db.session.add(appointment)
        db.session.commit()
        app.config["PREVIEW_DAY"] = start.date().isoformat()
    return app


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.app = make_frontend_test_app()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def sign_in(self, username):
        return self.client.post(
            "/auth/login", data={"username": username, "password": PREVIEW_PASSWORD}
        )

    def test_only_referenced_html_templates_exist(self):
        expected = {
            "home/index.html", "auth/login.html", "auth/register.html",
            "customer/dashboard.html", "contractor/dashboard.html",
        }
        templates = Path(self.app.template_folder)
        if not templates.is_absolute():
            templates = Path(self.app.root_path) / templates
        actual = {str(path.relative_to(templates)) for path in templates.rglob("*.html")}
        referenced = set()
        for route_file in (Path(self.app.root_path) / "routes").glob("*.py"):
            for node in ast.walk(ast.parse(route_file.read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "render_template":
                    referenced.add(node.args[0].value)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, referenced)

    def test_routes_match_supported_endpoints(self):
        self.assertEqual(
            {rule.rule for rule in self.app.url_map.iter_rules()},
            {"/", "/auth/login", "/auth/register", "/auth/logout",
             "/customer/create_appointment/<int:contractor_id>",
             "/customer/cancel_appointment/<int:appointment_id>",
             "/customer/reschedule_appointment/<int:appointment_id>",
             "/contractor/confirm_appointment/<int:appointment_id>",
             "/contractor/reject_appointment/<int:appointment_id>",
             "/contractor/reschedule_appointment/<int:appointment_id>",
             "/contractor/cancel_appointment/<int:appointment_id>",
             "/customer/dashboard", "/contractor/dashboard", "/contractor/schedule", "/static/<path:filename>"},
        )

    def test_public_pages_and_static_assets_render(self):
        for url in ("/", "/auth/login", "/auth/register", "/static/css/site.css", "/static/js/site.js"):
            with self.subTest(url=url):
                with self.client.get(url) as response:
                    self.assertEqual(response.status_code, 200)
        self.assertIn(b'for="display_name"', self.client.get("/auth/register").data)

    def test_failed_login_renders_error_and_preserves_username_only(self):
        response = self.client.post(
            "/auth/login", data={"username": "alex", "password": "wrong-password-sentinel"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'role="alert"', response.data)
        self.assertIn(b'value="alex"', response.data)
        self.assertNotIn(b"wrong-password-sentinel", response.data)

    def test_signup_creates_customer_and_success_feedback(self):
        response = self.client.post("/auth/register", data={
            "display_name": "New Customer", "username": "new_customer", "password": PREVIEW_PASSWORD,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your account is ready", response.data)
        with self.app.app_context():
            user = User.query.filter_by(username="new_customer").one()
            self.assertIsInstance(user, Customer)
            self.assertEqual(user.display_name, "New Customer")

    def test_duplicate_and_missing_registration_fields_render_errors(self):
        for data in [
            {"display_name": "Alex", "username": "alex", "password": PREVIEW_PASSWORD},
            {"username": "missing_name", "password": PREVIEW_PASSWORD},
        ]:
            with self.subTest(data=data["username"]):
                response = self.client.post("/auth/register", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'role="alert"', response.data)
                self.assertNotIn(PREVIEW_PASSWORD.encode(), response.data)

    def test_dashboard_login_guards_and_role_redirects(self):
        for url in ("/customer/dashboard", "/contractor/dashboard", "/auth/logout"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/auth/login", response.location)
        self.assertEqual(self.sign_in("alex").location, "/customer/dashboard")
        self.assertEqual(self.client.get("/contractor/dashboard").location, "/customer/dashboard")
        self.client.get("/auth/logout")
        self.assertEqual(self.sign_in("sam").location, "/contractor/dashboard")
        self.assertEqual(self.client.get("/customer/dashboard").location, "/contractor/dashboard")

    def test_customer_calendar_keeps_other_customer_details_private(self):
        self.sign_in("alex")
        response = self.client.get("/customer/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-schedule-calendar="customer"', response.data)
        self.assertIn(b"Awaiting reply", response.data)
        self.assertNotIn(b"Nina Patel", response.data)
        self.assertNotIn(b"private_customer", response.data)

    def test_contractor_sees_schedule_and_pending_requests(self):
        self.sign_in("sam")
        response = self.client.get("/contractor/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-schedule-calendar="contractor"', response.data)
        self.assertIn(b"Nina Patel", response.data)
        self.assertIn(b"Awaiting your reply", response.data)

    def test_customer_empty_state_and_escaped_long_name(self):
        with self.app.app_context():
            user = User.query.filter_by(username="robin").one()
            user.display_name = '<script>alert("xss")</script> ' + "Very long customer name " * 4
            db.session.commit()
        self.sign_in("robin")
        response = self.client.get("/customer/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your appointments will appear here", response.data)
        self.assertNotIn(b'<script>alert("xss")</script>', response.data)
        self.assertIn(b"&lt;script&gt;", response.data)

    def test_missing_schedule_preserves_dashboard_with_retry_action(self):
        self.sign_in("alex")
        with patch("app.routes.customer_routes.get_booking_schedule", side_effect=ValueError("No schedule")):
            with self.assertLogs(self.app.logger, level=logging.ERROR):
                response = self.client.get("/customer/dashboard")
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Try loading the calendar again", response.data)
        self.assertIn(b"Your appointments", response.data)

    def test_logout_returns_home_and_removes_login(self):
        self.sign_in("alex")
        response = self.client.get("/auth/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You have been signed out", response.data)
        self.assertIn("/auth/login", self.client.get("/customer/dashboard").location)


if __name__ == "__main__":
    unittest.main()
