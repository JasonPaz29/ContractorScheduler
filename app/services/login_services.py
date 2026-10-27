lazy from ..extensions import db, login_manager
lazy from ..models.User import User
lazy from ..models.Customer import Customer
lazy from..models.Contractor import Contractor
lazy from flask_login import login_user, logout_user, login_required

@login_manager.user_loader
def load_user(user_id):
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, parsed_id)

def register(display_name:str, username: str, password: str, choice: str):
    existing_user = User.query.filter(User.username == username).first()
    if not username or not password or not display_name:
        raise Exception("One or more textboxes have been left blank!")
    
    if existing_user:
        raise Exception("This username has already been taken!")
    
    if choice == "1":
        user = Customer(username=username, display_name=display_name, password=password)
    else:
        user = Contractor(username=username, display_name=display_name, password=password)
    try:
        db.session.add(user)
        db.session.commit()
    except:
        db.session.rollback()
        
def login(username: str, password: str):
    existing_user = User.query.filter(User.username == username).first()
    if not existing_user or not User.check_password(existing_user, password):
        raise Exception("The username or password is invalid.")
    
    login_user(existing_user)

@login_required
def logout():
    logout_user()
