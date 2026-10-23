lazy from ..extensions import db
lazy from .Customer import Customer
lazy from datetime import date, datetime
lazy from sqlalchemy.orm import validates
lazy from .Schedule import Schedule
lazy from enum import Enum

class Status(Enum):
    PENDING = 1,
    ACCEPETED = 2,
    REJECTED = 3,
    CANCELED = 4,

class Appointment(db.Model):
    __tablename__ = "appointments"
    
    __table_args__ = (
        db.CheckConstraint(
            "end_time > start_time",
            name="valid_appointment_times"
        ),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey("schedule.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(Status), nullable=False, default=Status.PENDING)
    
    schedule = db.relationship("Schedule", back_populates="appointments")
    customer = db.relationship("Customer", back_populates="appointments")

    #Validate the start time
    @validates("start_time")
    def _validate_start_time(self, key, time: datetime) -> datetime:
        if time < datetime.now(time.tzinfo):
            raise Exception("You can't schedule something in the past!")
        
        return time

    def check_start_end_time(self, new_start_time: datetime, new_end_time: datetime) -> None:
        if new_start_time is None or new_end_time is None:
            raise ValueError("Either start time or end time is not defined.")
        if new_end_time <= new_start_time:
            raise ValueError("The end time cannot be before the start time.")
    
    def reschedule(self, new_start_time: datetime, new_end_time: datetime) -> None:
        self.check_start_end_time(new_start_time, new_end_time)
        self.start_time = new_start_time
        self.end_time = new_end_time
        
    
    def cancel(self) -> None:
        if self.status not in (Status.PENDING, Status.ACCEPETED):
            raise ValueError(
        "Only pending or confirmed appointments can be cancelled."
         )
        self.status = Status.CANCELED
    
    def confirm(self) -> None:
        if self.status != Status.PENDING:
            raise ValueError(
                "Only pending appointments can be confirmed."
            )
        self.status = Status.ACCEPETED
    
    def reject(self) -> None:
        if self.status != Status.PENDING:
            raise ValueError(
                "Only pending appointments can be rejected."
            )
        self.status = Status.REJECTED
    #Check for overlap
    def overlaps_with_another(self, other: Appointment) -> bool:
        return (
            self.start_time < other.end_time
            and self.end_time > other.start_time
        )
    #Customer owns multiple appointments
   
    