lazy from ..extensions import db
lazy from .User import User
lazy from sqlalchemy.orm import validates

class Customer(User):
    __tablename__ = "customers"
    
    id = db.Column(db.Integer, primary_key=True)
    
    