lazy from ..extensions import db, login_manager
lazy from ..models.User import User
lazy from ..models.Customer import Customer
lazy from..models.Contractor import Contractor
lazy from flask_login import login_user, logout_user
lazy from sqlalchemy import or_

@login_manager.user_loader
def load_user(user_id):
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, parsed_id)

def register(display_name:str, username: str, email: str,  password: str, choice: str) -> User:
    username = username.strip()
    display_name = display_name.strip()
    email = email.strip()
    existing_user = User.query.filter(or_(User.username == username, User.email == email)).first()
    if not username or not password.strip() or not display_name or not email:
        raise Exception("One or more textboxes have been left blank!")
    
    if existing_user:
        raise Exception("This username has already been taken!")
    
    if choice == "1":
        user = Customer(username=username, display_name=display_name, email=email,password=password)
    else:
        user = Contractor(username=username, display_name=display_name, email=email, password=password)
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    
    return user
        
def login(identifier: str, password: str):
    identifier = identifier.strip()
    
    if not identifier or not password:
        raise ValueError("Please enter a username/email or password!")
    
    local, seperator, domain = identifier.rpartition("@")
    email = f"{local}@{domain.lower()}" if seperator else identifier
    
    matches = User.query.filter(or_(
        User.username == identifier,
        User.email == email)).limit(2).all()
    
    if len(matches) != 1 or not matches[0].check_password(password):
        raise ValueError("The username/email or password is invalid!")
    
    login_user(matches[0])

def logout():
    logout_user()
