from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Appointment, Patient, Provider
from ..schemas import DoctorAppointmentOut, ProviderOut
from ..security import get_current_provider
from ..services.scheduling import clinic_now

router = APIRouter(prefix="/doctor", tags=["doctor"])


def _age(dob: date | None) -> int | None:
    if not dob:
        return None
    t = date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


@router.get("/me", response_model=ProviderOut)
def me(provider: Provider = Depends(get_current_provider)):
    return provider


@router.get("/appointments", response_model=list[DoctorAppointmentOut])
def appointments(provider: Provider = Depends(get_current_provider), db: Session = Depends(get_db)):
    since = clinic_now() - timedelta(days=7)
    rows = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient).joinedload(Patient.user))
        .filter(Appointment.provider_id == provider.id, Appointment.start_time >= since)
        .order_by(Appointment.start_time)
        .all()
    )
    return [
        DoctorAppointmentOut(
            id=a.id,
            start_time=a.start_time,
            end_time=a.end_time,
            status=a.status,
            reason=a.reason,
            ai_summary=a.ai_summary,
            patient_name=a.patient.user.full_name,
            patient_age=_age(a.patient.date_of_birth),
            patient_sex=a.patient.sex,
            patient_conditions=a.patient.conditions or [],
            patient_medications=a.patient.medications or [],
            patient_allergies=a.patient.allergies or [],
        )
        for a in rows
    ]
