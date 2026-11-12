lazy from ..extensions import db
lazy from flask_login import UserMixin
lazy from werkzeug.security import generate_password_hash, check_password_hash
lazy from sqlalchemy.orm import Mapped, mapped_column, validates
lazy from ..services.profanity_check import contains_profanity
lazy from re import fullmatch

class User(db.Model, UserMixin):
    __tablename__ = "users"
    
    def __init__(self, display_name: str, username: str, email:str, password: str) -> None:
        self.display_name = display_name
        self.username = username
        self.email = email
        self.password = password
        

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(db.String(155), nullable=False)
    username: Mapped[str] = mapped_column(db.String(200), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(db.String(20), nullable=False, default="customer")
    
    __mapper_args__ = {
        "polymorphic_on": "account_type",
        "polymorphic_identity": "user",
    }
    def hash_password(self, password: str) -> str:
        return generate_password_hash(password=password)
    
    def check_password(self, password_guess: str) -> bool:
        return check_password_hash(pwhash=self.password, password=password_guess)
    
    #Automatically hash the password
    @validates("password")
    def _hash_password_on_assignment(self, key, password: str) -> str:
        return self.hash_password(password)
    
    @validates("username")
    def _confirm_username_has_no_profanity(self, key, username: str) -> str:
        if contains_profanity(username):
            raise Exception("Your username has profanity in it!")
        return username
    @validates("email")
    def _confirm_email_is_valid(self, key, email: str) -> str:
        """Validate common ASCII email addresses and normalize the domain."""
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Please enter an email address.")

        email = email.strip()
        local_part, separator, domain = email.rpartition("@")
        # Unquoted local parts may contain dots between nonempty atoms.
        atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
        domain_label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        if (
            len(email) > 254
            or len(local_part) > 64
            or not separator
            or fullmatch(rf"{atom}(?:\.{atom})*", local_part) is None
            or fullmatch(rf"{domain_label}(?:\.{domain_label})+", domain) is None
            or domain.rsplit(".", 1)[-1].isdigit()
        ):
            raise ValueError("Please enter a valid email address, such as name@example.com.")

        # Preserve the local part: it may be case-sensitive.
        return f"{local_part}@{domain.lower()}"

