lazy from ..extensions import db
lazy from flask_login import UserMixin
lazy from werkzeug.security import generate_password_hash, check_password_hash
lazy from sqlalchemy.orm import Mapped, mapped_column, validates
lazy from ..services.profanity_check import contains_profanity

#TODO Add Email attribute
class User(db.Model, UserMixin):
    __tablename__ = "users"
    
    def __init__(self, display_name: str, username: str, password: str) -> None:
        self.display_name = display_name
        self.username = username
        self.password = password

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(db.String(155), nullable=False)
    username: Mapped[str] = mapped_column(db.String(200), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)
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

