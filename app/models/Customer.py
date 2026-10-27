lazy from ..extensions import db
lazy from .User import User
lazy from sqlalchemy.orm import Mapped, mapped_column, relationship
lazy from .Appointment import Appointment, Status
lazy from datetime import datetime
lazy from .Schedule import Schedule

class Customer(User):
    __tablename__ = "customers"
    
    id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True)
    
    #Mapped for VSCode issues.
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    
    def request_appointment(self, start_time: datetime, end_time: datetime, schedule: Schedule) -> Appointment:
        appointment = Appointment()
        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.customer_id = self.id
        appointment.schedule_id = schedule.id
        
        return appointment
    
    def cancel_appointment(self, appointment: Appointment) -> None:
        if self.id is None or self.id != appointment.customer_id:
            raise ValueError("This appointment does not belong to you!")
        appointment.cancel()
    
    def get_pending_appointments(self) -> list[Appointment]:
        pending_appointments = list()
        
        for appointment in self.appointments:
            if appointment.status == Status.PENDING:
                pending_appointments.append(appointment)
        
        return pending_appointments

    def get_upcoming_appointments(self) -> list[Appointment]:
        upcoming_appointments = list()
        
        for appointment in self.appointments:
            if appointment.start_time > datetime.now(appointment.start_time.tzinfo) and appointment.status == Status.ACCEPETED:
                upcoming_appointments.append(appointment)
        return upcoming_appointments
