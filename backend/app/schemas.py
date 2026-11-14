from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    date_of_birth: date | None = None
    sex: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PatientProfile(ORM):
    full_name: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    phone: str | None = None
    conditions: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []
    surgeries: list[str] = []
    family_history: list[str] = []
    notes: str | None = None


class ProviderOut(ORM):
    id: int
    name: str
    specialty: str
    title: str
    years_experience: int
    rating: float
    reviews_count: int
    bio: str
    location: str
    languages: list[str]
    photo_url: str | None
    accepts_new: bool


class MessageOut(ORM):
    id: int
    role: str
    content: str
    payload: dict | None = None
    created_at: datetime


class ConversationOut(ORM):
    id: str
    title: str
    phase: str
    specialty: str | None
    urgency: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
    state: dict


class SendMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class SendMessageOut(BaseModel):
    messages: list[MessageOut]
    state: dict
    trace: list[str]
    conversation: ConversationOut


class Slot(BaseModel):
    start: datetime
    end: datetime


class DaySlots(BaseModel):
    date: date
    slots: list[Slot]


class BookIn(BaseModel):
    provider_id: int
    start_time: datetime
    conversation_id: str | None = None


class AppointmentOut(ORM):
    id: int
    provider: ProviderOut
    start_time: datetime
    end_time: datetime
    status: str
    reason: str | None
    conversation_id: str | None
    ai_summary: dict | None = None


class DoctorAppointmentOut(ORM):
    id: int
    start_time: datetime
    end_time: datetime
    status: str
    reason: str | None
    ai_summary: dict | None
    patient_name: str
    patient_age: int | None
    patient_sex: str | None
    patient_conditions: list[str]
    patient_medications: list[str]
    patient_allergies: list[str]
