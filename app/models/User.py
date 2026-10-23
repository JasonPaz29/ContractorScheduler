lazy from ..extensions import db
lazy from flask_login import UserMixin
lazy from werkzeug.security import generate_password_hash, check_password_hash
lazy from sqlalchemy.orm import validates
lazy from ..services.profanity_check import contains_profanity


class User(db.Model, UserMixin):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(155), nullable=False)
    username = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

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
    