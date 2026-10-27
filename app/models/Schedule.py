lazy from ..extensions import db
lazy from sqlalchemy.orm import Mapped, mapped_column, relationship
lazy from .Appointment import Appointment, Status
lazy from .Contractor import Contractor
lazy from datetime import datetime, date

class Schedule(db.Model):
    __tablename__ = "schedule"
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    contractor_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("contractors.id"), nullable=False)
    max_daily_appointments: Mapped[int] = mapped_column(db.Integer, nullable=False, default=6)
    
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="schedule", cascade="all, delete-orphan", lazy="selectin")
    contractor: Mapped["Contractor"] = relationship("Contractor", back_populates="schedule")
    
    def get_appointments_for_day(self, day: date) -> list[Appointment]:
        todays_appointments = list()
        for appointment in self.appointments:
            if appointment.start_time.date() == day:
                todays_appointments.append(appointment)
        return todays_appointments

    def check_conflict(self, other: Appointment) -> bool:
        for appointment in self.appointments:
            if appointment is other:
                continue
            if appointment.schedule_id != self.id:
                raise ValueError("This appointment is not apart of the schedule!")
            if (other.overlaps_with_another(appointment) and appointment.status == Status.ACCEPETED):
                return True
        return False
    #Return True if capacity is reached, otherwise False.
    def check_daily_capacity(self, day: date, exclude: Appointment | None = None) -> bool:
        today_appointments = list()
        for appointment in self.get_appointments_for_day(day):
            if appointment is exclude:
                continue
            if appointment.status == Status.ACCEPETED:
                today_appointments.append(appointment) 
        if len(today_appointments) >= self.max_daily_appointments:
            return True
        return False
    
    def can_accept(self, appointment: Appointment):
        if self.check_conflict(appointment) or self.check_daily_capacity(appointment.start_time.date(), exclude=appointment):
            return False
        return True

