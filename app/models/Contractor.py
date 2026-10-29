lazy from .User import User
lazy from ..extensions import db
lazy from datetime import datetime
lazy from sqlalchemy.orm import validates, Mapped, mapped_column, relationship
lazy from .Appointment import Appointment, Status
lazy from .Schedule import Schedule

class Contractor(User):
    __tablename__ = "contractors"
    id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True)
    
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="contractor", cascade="all, delete-orphan", lazy="selectin")
    
    __mapper_args__ = {
            "polymorphic_identity": "contractor",
        }
    def _validate_appointment_ownership(self, appointment: Appointment) -> None:
        if self.schedule is None:
            raise ValueError("This contractor has no schedule!")

        if appointment.schedule_id != self.schedule.id:
            raise ValueError("This appointment belongs to a different schedule!")
    def confirm_appointment(self, appointment: Appointment) -> bool:
        self._validate_appointment_ownership(appointment)
        if not self.schedule.can_accept(appointment):
            return False

        appointment.confirm()
        return True

    def reject_appointment(self, appointment: Appointment) -> bool:
        self._validate_appointment_ownership(appointment)
        appointment.reject()
        return True
    #This is needed in case Contractor needs to cancel a confirmed appointment
    def cancel_appointment(self, appointment: Appointment) -> bool:
        self._validate_appointment_ownership(appointment)
        appointment.cancel()
        return True

    def reschedule_appointment(self, appointment: Appointment, new_start: datetime, new_end: datetime) -> None:
        self._validate_appointment_ownership(appointment)
        appointment.check_start_end_time(new_start, new_end)
        appointment.reschedule(new_start, new_end)


