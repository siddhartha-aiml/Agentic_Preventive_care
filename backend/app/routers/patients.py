from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Patient
from ..schemas import PatientProfile
from ..security import get_current_patient

router = APIRouter(prefix="/patients", tags=["patients"])

LIST_FIELDS = ("conditions", "medications", "allergies", "surgeries", "family_history")


def _profile(p: Patient) -> PatientProfile:
    return PatientProfile(
        full_name=p.user.full_name,
        email=p.user.email,
        date_of_birth=p.date_of_birth,
        sex=p.sex,
        phone=p.phone,
        notes=p.notes,
        **{f: getattr(p, f) or [] for f in LIST_FIELDS},
    )


@router.get("/me", response_model=PatientProfile)
def get_me(patient: Patient = Depends(get_current_patient)):
    return _profile(patient)


@router.put("/me", response_model=PatientProfile)
def update_me(body: PatientProfile, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    patient = db.merge(patient)
    if body.full_name:
        patient.user.full_name = body.full_name.strip()
    for field in ("date_of_birth", "sex", "phone", "notes"):
        setattr(patient, field, getattr(body, field))
    for field in LIST_FIELDS:
        setattr(patient, field, [s.strip() for s in getattr(body, field) if s and s.strip()])
    db.commit()
    db.refresh(patient)
    return _profile(patient)
