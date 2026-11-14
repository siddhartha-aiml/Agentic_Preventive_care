import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="patient")  # patient | doctor
    full_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped["Patient | None"] = relationship(back_populates="user", uselist=False)
    provider: Mapped["Provider | None"] = relationship(back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    surgeries: Mapped[list] = mapped_column(JSON, default=list)
    family_history: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="patient")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(120))
    years_experience: Mapped[int] = mapped_column(Integer, default=5)
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    bio: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    languages: Mapped[list] = mapped_column(JSON, default=list)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accepts_new: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User | None] = relationship(back_populates="provider")
    cases: Mapped[list["ProviderCase"]] = relationship(back_populates="provider", cascade="all, delete-orphan")
    availability: Mapped[list["Availability"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class ProviderCase(Base):
    """De-identified historical case treated by a provider (used for similarity matching)."""

    __tablename__ = "provider_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    symptoms: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str] = mapped_column(String(255))
    outcome: Mapped[str] = mapped_column(String(255), default="")
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    provider: Mapped[Provider] = relationship(back_populates="cases")


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = Monday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)

    provider: Mapped[Provider] = relationship(back_populates="availability")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        # Only one *active* booking per provider + start time.
        Index(
            "uq_active_appointment",
            "provider_id",
            "start_time",
            unique=True,
            sqlite_where=text("status = 'booked'"),
            postgresql_where=text("status = 'booked'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="booked")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[Patient] = relationship()
    provider: Mapped[Provider] = relationship()


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="New consultation")
    phase: Mapped[str] = mapped_column(String(20), default="intake")
    specialty: Mapped[str | None] = mapped_column(String(80), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ConsultationSummary(Base):
    __tablename__ = "consultation_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(String(80), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
