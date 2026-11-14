

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..models import Appointment, Conversation, Message, Patient, Provider, utcnow
from ..schemas import AppointmentOut, BookIn
from ..security import get_current_patient
from ..services.scheduling import SlotUnavailable, book
from .conversations import graph_state

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _ai_summary(db: Session, conv: Conversation | None, patient: Patient) -> tuple[dict, str | None]:
    history = {
        "conditions": patient.conditions or [],
        "medications": patient.medications or [],
        "allergies": patient.allergies or [],
    }
    if not conv:
        return {"history": history}, None
    state = graph_state(conv.id)
    cls = state.get("classification") or {}
    qa = [{"role": m.role, "content": m.content} for m in conv.messages if m.role in ("user", "assistant")][-12:]
    summary = {
        "symptom_summary": state.get("symptom_summary"),
        "specialty": cls.get("specialty"),
        "urgency": cls.get("urgency"),
        "reasoning": cls.get("reasoning"),
        "emergency": bool(state.get("emergency")),
        "history": history,
        "transcript": qa,
    }
    return summary, cls.get("title") or conv.title


@router.get("", response_model=list[AppointmentOut])
def list_appointments(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.provider))
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.start_time.desc())
        .all()
    )


@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(body: BookIn, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    provider = db.get(Provider, body.provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    conv = None
    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if not conv or conv.patient_id != patient.id:
            raise HTTPException(404, "Conversation not found")
    summary, reason = _ai_summary(db, conv, patient)
    try:
        appt = book(
            db,
            patient_id=patient.id,
            provider_id=provider.id,
            start_time=body.start_time,
            conversation_id=conv.id if conv else None,
            reason=reason,
            ai_summary=summary,
        )
    except SlotUnavailable as e:
        raise HTTPException(409, str(e))
    if conv:
        db.add(
            Message(
                conversation_id=conv.id,
                role="system",
                content=f"Appointment booked with {provider.name} on {appt.start_time:%A, %B %d at %I:%M %p}.",
                payload={
                    "type": "booking",
                    "appointment_id": appt.id,
                    "provider_name": provider.name,
                    "specialty": provider.specialty,
                    "start_time": appt.start_time.isoformat(),
                    "location": provider.location,
                },
            )
        )
        conv.updated_at = utcnow()
        db.commit()
    db.refresh(appt)
    return appt


@router.post("/{appt_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appt_id: int, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    appt = db.get(Appointment, appt_id)
    if not appt or appt.patient_id != patient.id:
        raise HTTPException(404, "Appointment not found")
    if appt.status != "booked":
        raise HTTPException(400, "Appointment is not active")
    appt.status = "cancelled"
    db.commit()
    db.refresh(appt)
    return appt
