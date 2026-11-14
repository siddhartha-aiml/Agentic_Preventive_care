"""LLM factory and structured-output schemas. All fields are required to stay compatible with OpenAI strict JSON schema."""

import logging
import time
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

from ..config import get_settings
from .specialties import SpecialtyName

settings = get_settings()
log = logging.getLogger(__name__)

# Last outcome of real OpenAI calls, so silent fallbacks are visible via /api/meta.
LLM_HEALTH: dict = {"last_ok": None, "last_error": None, "last_error_type": None}


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


def record_llm_ok() -> None:
    LLM_HEALTH["last_ok"] = time.time()


def record_llm_error(exc: Exception) -> None:
    LLM_HEALTH["last_error"] = time.time()
    LLM_HEALTH["last_error_type"] = type(exc).__name__


def invoke_structured(schema: type[BaseModel], messages: list):
    """Call the chat model with structured output, recording success/failure."""
    try:
        result = structured(schema).invoke(messages)
    except Exception as exc:
        record_llm_error(exc)
        raise
    record_llm_ok()
    return result


def agent_mode() -> str:
    if settings.demo_mode:
        return "demo"
    ok, err = LLM_HEALTH["last_ok"], LLM_HEALTH["last_error"]
    if err and (not ok or err > ok):
        return "degraded"
    return "gpt"
