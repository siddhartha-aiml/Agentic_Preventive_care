"""LLM factory and structured-output schemas. All fields are required to stay compatible with OpenAI strict JSON schema."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

from ..config import get_settings
from .specialties import SpecialtyName

settings = get_settings()


class IntakeDecision(BaseModel):
    red_flag: bool = Field(description="True only if emergency warning signs are present")
    red_flag_reason: str = Field(description="Why this is an emergency, or empty string")
    action: Literal["ask", "complete"]
    question: str = Field(description="The single follow-up question (or the hand-off sentence when complete)")
    symptom_summary: str = Field(description="Clinical-style summary when complete, otherwise empty string")


class SpecialtyClassification(BaseModel):
    specialty: SpecialtyName
    secondary_specialty: SpecialtyName
    confidence: float = Field(description="0.0 to 1.0")
    urgency: Literal["routine", "soon", "urgent", "emergency"]
    reasoning: str
    title: str


class ProviderReason(BaseModel):
    provider_id: int
    reason: str


class ProviderReasons(BaseModel):
    items: list[ProviderReason]


class ConciergeDecision(BaseModel):
    intent: Literal["question", "new_symptoms"]
    reply: str


@lru_cache
def chat_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, timeout=60, max_retries=2)


def structured(schema: type[BaseModel]):
    return chat_model().with_structured_output(schema)
