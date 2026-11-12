import unittest

from app.models.User import User
from app.models.Customer import Customer
from app.models.Contractor import Contractor
# Register relationship targets before SQLAlchemy configures the user subclasses.
from app.models import Appointment, Schedule


class UserEmailTests(unittest.TestCase):
    def setUp(self):
        self.user = User("Email Test", "email_test_user", "email_test@example.com", "test-password")

    def test_assignment_trims_whitespace_and_normalizes_only_domain(self):
        self.user.email = "  Alex.Tag+bookings@EXAMPLE.COM  "
        self.assertEqual(self.user.email, "Alex.Tag+bookings@example.com")

    def test_common_addresses_are_accepted(self):
        for email in ("alex@example.com", "o'connor@example.co.uk", "a+b@sub.example.com"):
            with self.subTest(email=email):
                self.user.email = email
                self.assertEqual(self.user.email, email)

    def test_bad_addresses_raise_and_preserve_previous_value(self):
        self.user.email = "alex@example.com"
        invalid = (
            None, 123, "", "   ", "alex", "alex@", "@example.com",
            "alex@@example.com", ".alex@example.com", "alex.@example.com",
            "alex..tag@example.com", "alex smith@example.com", "alex@localhost",
            "alex@-example.com", "alex@example-.com", "alex@exam_ple.com",
            "alex@example..com", "alex@example.com.", "alex@127.0.0.1",
            "Alex <alex@example.com>", "alex@example.com\r\nBcc: other@example.com",
        )
        for email in invalid:
            with self.subTest(email=email):
                with self.assertRaises(ValueError):
                    self.user.email = email
                self.assertEqual(self.user.email, "alex@example.com")

    def test_local_part_and_domain_label_lengths(self):
        self.user.email = "a" * 64 + "@example.com"
        self.user.email = "a@" + "b" * 63 + ".com"
        for email in ("a" * 65 + "@example.com", "a@" + "b" * 64 + ".com"):
            with self.subTest(email=email):
                with self.assertRaises(ValueError):
                    self.user.email = email

    def test_total_address_length(self):
        longest = "a" * 64 + "@" + "b" * 63 + "." + "c" * 63 + "." + "d" * 61
        self.assertEqual(len(longest), 254)
        self.user.email = longest
        with self.assertRaises(ValueError):
            self.user.email = longest + "d"

    def test_customer_and_contractor_inherit_assignment_validation(self):
        for user_type in (Customer, Contractor):
            with self.subTest(user_type=user_type.__name__):
                user = user_type("Email Test", "email_test_user", "email_test@example.com", "test-password")
                user.email = "alex@EXAMPLE.COM"
                self.assertEqual(user.email, "alex@example.com")
                with self.assertRaises(ValueError):
                    user.email = "invalid"


if __name__ == "__main__":
    unittest.main()
