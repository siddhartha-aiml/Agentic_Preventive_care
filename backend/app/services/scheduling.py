"""Slot generation and booking. Times are naive datetimes in the clinic's local timezone."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Appointment, Availability

settings = get_settings()


class SlotUnavailable(Exception):
    pass


def clinic_now() -> datetime:
    return datetime.now(ZoneInfo(settings.clinic_timezone)).replace(tzinfo=None, second=0, microsecond=0)


def _booked_starts(db: Session, provider_id: int, start: datetime, end: datetime) -> set[datetime]:
    rows = (
        db.query(Appointment.start_time)
        .filter(
            Appointment.provider_id == provider_id,
            Appointment.status == "booked",
            Appointment.start_time >= start,
            Appointment.start_time < end,
        )
        .all()
    )
    return {r[0] for r in rows}


def open_slots(db: Session, provider_id: int, days: int | None = None, now: datetime | None = None) -> list[tuple[datetime, datetime]]:
    days = days or settings.booking_window_days
    now = now or clinic_now()
    earliest = now + timedelta(hours=2)  # minimum notice
    horizon_end = datetime.combine(now.date() + timedelta(days=days + 1), datetime.min.time())
    rules = db.query(Availability).filter(Availability.provider_id == provider_id).all()
    by_day: dict[int, list[Availability]] = defaultdict(list)
    for r in rules:
        by_day[r.weekday].append(r)

    booked = _booked_starts(db, provider_id, now, horizon_end)
    slots: list[tuple[datetime, datetime]] = []
    for offset in range(days + 1):
        day: date = now.date() + timedelta(days=offset)
        for rule in sorted(by_day.get(day.weekday(), []), key=lambda r: r.start_time):
            cursor = datetime.combine(day, rule.start_time)
            block_end = datetime.combine(day, rule.end_time)
            step = timedelta(minutes=rule.slot_minutes)
            while cursor + step <= block_end:
                if cursor >= earliest and cursor not in booked:
                    slots.append((cursor, cursor + step))
                cursor += step
    return slots


def slots_by_day(db: Session, provider_id: int, days: int | None = None) -> list[dict]:
    grouped: dict[date, list[dict]] = defaultdict(list)
    for s, e in open_slots(db, provider_id, days):
        grouped[s.date()].append({"start": s, "end": e})
    return [{"date": d, "slots": grouped[d]} for d in sorted(grouped)]


def next_available(db: Session, provider_id: int, days: int = 14) -> datetime | None:
    slots = open_slots(db, provider_id, days)
    return slots[0][0] if slots else None


def book(
    db: Session,
    *,
    patient_id: int,
    provider_id: int,
    start_time: datetime,
    conversation_id: str | None,
    reason: str | None,
    ai_summary: dict | None,
) -> Appointment:
    start_time = start_time.replace(tzinfo=None, second=0, microsecond=0)
    match = next(((s, e) for s, e in open_slots(db, provider_id) if s == start_time), None)
    if not match:
        raise SlotUnavailable("That time is no longer available.")
    appt = Appointment(
        patient_id=patient_id,
        provider_id=provider_id,
        conversation_id=conversation_id,
        start_time=match[0],
        end_time=match[1],
        status="booked",
        reason=reason,
        ai_summary=ai_summary,
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:  # concurrent booking hit the unique index
        db.rollback()
        raise SlotUnavailable("That time was just booked by someone else.")
    db.refresh(appt)
    return appt
