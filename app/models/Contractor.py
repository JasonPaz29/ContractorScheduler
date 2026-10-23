lazy from .User import User
lazy from ..extensions import db
lazy from sqlalchemy.orm import validates
lazy from .Appointment import Appointment

class Contractor(User):
    __tablename__ = "contractors"
    id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True)
    
    
    
    