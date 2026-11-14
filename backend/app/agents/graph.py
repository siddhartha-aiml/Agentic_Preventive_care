"""LangGraph orchestration for Your Health Guide.

Turn flow (one invocation per patient message, state restored from the checkpointer by thread_id):

    START → load_context ─┬─ phase=intake ─────► intake_agent ─┬─ ask ─────────► END
                          │                                    ├─ red flag ──► emergency ─► classify_specialty
                          │                                    └─ complete ──────────────► classify_specialty
                          │                                       classify_specialty → match_providers → summarize_memory → END
                          └─ phase=recommended ► concierge ─┬─ question ─► END
                                                            └─ new symptoms ─► intake_agent
"""

import logging
import sqlite3
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from ..config import get_settings
from ..db import SessionLocal
from ..models import ConsultationSummary, Patient, Provider, ProviderCase, User
from ..services.scheduling import clinic_now, next_available
from ..services.similarity import score_cases
from . import fallback
from .llm import ConciergeDecision, IntakeDecision, ProviderReasons, SpecialtyClassification, invoke_structured
from .prompts import (
    CLASSIFIER_SYSTEM,
    CONCIERGE_SYSTEM,
    INTAKE_SYSTEM,
    MATCHER_SYSTEM,
    SAFETY_POLICY,
    render_patient_context,
)
from .specialties import specialty_catalogue_text

log = logging.getLogger(__name__)
settings = get_settings()

TOP_K = 4
MIN_RECS = 3
RELEVANT_CASE_SIM = 0.2


class HealthState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    patient_id: int
    conversation_id: str
    patient_context: str
    phase: str  # intake | recommended
    followup_count: int
    symptom_summary: str
    classification: dict | None
    recommendations: list[dict]
    emergency: dict | None
    trace: list[str]
    # transient routing hints
    _intake_action: str
    _concierge_intent: str


# ───────────────────────── helpers ─────────────────────────

def _user_texts(messages: list[AnyMessage]) -> list[str]:
    return [m.content for m in messages if isinstance(m, HumanMessage)]


def _since_last_reset(state: HealthState) -> list[AnyMessage]:
    """Messages of the current assessment (after the last concierge 'new assessment' marker)."""
    msgs = state.get("messages", [])
    for i in range(len(msgs) - 1, -1, -1):
        if isinstance(msgs[i], AIMessage) and msgs[i].additional_kwargs.get("assessment_start"):
            # include the user message that triggered the reset (just before the marker)
            start = i - 1 if i > 0 and isinstance(msgs[i - 1], HumanMessage) else i
            return msgs[start:]
    return msgs


def _chat_history(messages: list[AnyMessage]) -> list[AnyMessage]:
    return [m for m in messages if isinstance(m, (HumanMessage, AIMessage)) and m.content]


def _trace(state: HealthState, node: str) -> list[str]:
    return [*state.get("trace", []), node]


def _ai(content: str, payload: dict | None = None, **extra: Any) -> AIMessage:
    kwargs: dict[str, Any] = dict(extra)
    if payload:
        kwargs["payload"] = payload
    return AIMessage(content=content, additional_kwargs=kwargs)


# ───────────────────────── nodes ─────────────────────────

def load_context(state: HealthState) -> dict:
    with SessionLocal() as db:
        patient = db.get(Patient, state["patient_id"])
        user = db.get(User, patient.user_id)
        summaries = (
            db.query(ConsultationSummary)
            .filter(ConsultationSummary.patient_id == patient.id)
            .filter(ConsultationSummary.conversation_id != state.get("conversation_id"))
            .order_by(ConsultationSummary.created_at.desc())
            .limit(5)
            .all()
        )
        ctx = render_patient_context(patient, user, summaries)
    return {
        "patient_context": ctx,
        "trace": ["load_context"],
        "phase": state.get("phase") or "intake",
        "followup_count": state.get("followup_count", 0),
    }


def intake_agent(state: HealthState) -> dict:
    convo = _chat_history(_since_last_reset(state))
    count = state.get("followup_count", 0)
    decision: IntakeDecision | None = None
    if not settings.demo_mode:
        try:
            system = INTAKE_SYSTEM.format(
                safety=SAFETY_POLICY,
                patient_context=state.get("patient_context", ""),
                followup_count=count,
                max_followups=settings.max_followups,
            )
            decision = invoke_structured(IntakeDecision, [SystemMessage(system), *convo])
        except Exception:
            log.exception("Intake LLM failed; using fallback")
    if decision is None:
        decision = fallback.intake(_user_texts(convo), count, settings.max_followups, state.get("patient_context", ""))
    # Hard safety nets independent of the model.
    rule_flag = fallback.detect_red_flag(" ".join(_user_texts(convo)))
    if rule_flag and not decision.red_flag:
        decision.red_flag = True
        decision.red_flag_reason = f"You mentioned “{rule_flag}”, which can be a sign of a medical emergency."
    if decision.action == "ask" and count >= settings.max_followups:
        decision.action = "complete"
    if decision.red_flag:
        decision.action = "complete"
    if decision.action == "complete" and not decision.symptom_summary:
        decision.symptom_summary = " | ".join(_user_texts(convo))

    update: dict[str, Any] = {"trace": _trace(state, "intake_agent")}
    if decision.action == "ask":
        update["messages"] = [_ai(decision.question, {"type": "followup", "index": count + 1, "max": settings.max_followups})]
        update["followup_count"] = count + 1
        update["_intake_action"] = "ask"
    else:
        update["symptom_summary"] = decision.symptom_summary
        update["_intake_action"] = "emergency" if decision.red_flag else "complete"
        if decision.red_flag:
            update["emergency"] = {"reason": decision.red_flag_reason}
        else:
            update["messages"] = [_ai(decision.question or "Thanks — let me find the right specialist for you.")]
    return update


def emergency(state: HealthState) -> dict:
    reason = (state.get("emergency") or {}).get("reason", "")
    text = (
        "⚠️ **This may be a medical emergency.** "
        f"{reason} Please **call 112 (national emergency number) or 108 for an ambulance, or go to the nearest emergency room now**. "
        "If you are having thoughts of harming yourself, please call **Tele-MANAS at 14416** (or 1-800-891-4416), India's free 24/7 mental health helpline. "
        "\n\nIf you're safe and simply want follow-up care afterwards, I've listed suitable doctors below."
    )
    return {"messages": [_ai(text, {"type": "emergency", "reason": reason})], "trace": _trace(state, "emergency")}


def classify_specialty(state: HealthState) -> dict:
    convo = _chat_history(_since_last_reset(state))
    is_emergency = bool(state.get("emergency"))
    result: SpecialtyClassification | None = None
    if not settings.demo_mode:
        try:
            system = CLASSIFIER_SYSTEM.format(catalogue=specialty_catalogue_text(), patient_context=state.get("patient_context", ""))
            result = invoke_structured(SpecialtyClassification, 
                [SystemMessage(system), *convo, HumanMessage(f"Symptom summary for classification: {state.get('symptom_summary', '')}")]
            )
        except Exception:
            log.exception("Classifier LLM failed; using fallback")
    if result is None:
        result = fallback.classify(state.get("symptom_summary", "") + " " + " ".join(_user_texts(convo)), is_emergency)
    result.confidence = max(0.0, min(1.0, result.confidence))
    if result.confidence < 0.5 and result.specialty != "General Physician":
        result.secondary_specialty = result.specialty
        result.specialty = "General Physician"
    if is_emergency:
        result.urgency = "emergency"
    data = result.model_dump()
    msg = _ai(
        f"Based on what you've shared, I recommend seeing a **{result.specialty}** specialist. {result.reasoning}",
        {"type": "classification", **data},
    )
    return {"classification": data, "messages": [msg], "trace": _trace(state, "classify_specialty")}


def match_providers(state: HealthState) -> dict:
    cls = state.get("classification") or {}
    specialty = cls.get("specialty", "General Physician")
    summary = state.get("symptom_summary", "")
    with SessionLocal() as db:
        candidates = db.query(Provider).filter(Provider.specialty == specialty, Provider.accepts_new.is_(True)).all()
        # Only broaden the search when the primary specialty can't fill a minimum of 3 recommendations.
        for extra in [cls.get("secondary_specialty"), "General Physician"]:
            if len(candidates) >= MIN_RECS or not extra or extra == specialty:
                continue
            candidates += db.query(Provider).filter(Provider.specialty == extra, Provider.accepts_new.is_(True)).all()
        ids = [p.id for p in candidates]
        cases = db.query(ProviderCase).filter(ProviderCase.provider_id.in_(ids)).all() if ids else []
        sims = score_cases(db, summary, cases)

        scored = []
        for p in candidates:
            pcases = sorted((c for c in cases if c.provider_id == p.id), key=lambda c: sims.get(c.id, 0), reverse=True)
            top = [sims.get(c.id, 0.0) for c in pcases[:3]]
            similarity = (0.6 * top[0] + 0.4 * (sum(top) / len(top))) if top else 0.0
            nxt = next_available(db, p.id)
            soon = 1.0 if nxt and (nxt - clinic_now()).days <= 3 else 0.4 if nxt else 0.0
            specialty_bonus = 0.0 if p.specialty == specialty else -0.15
            score = 0.60 * similarity + 0.20 * (p.rating / 5) + 0.10 * min(p.years_experience / 25, 1) + 0.10 * soon + specialty_bonus
            scored.append((score, similarity, p, pcases[:3], nxt))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:TOP_K]

        recs = []
        for score, similarity, p, pcases, nxt in top:
            recs.append(
                {
                    "provider_id": p.id,
                    "name": p.name,
                    "specialty": p.specialty,
                    "title": p.title,
                    "rating": p.rating,
                    "reviews_count": p.reviews_count,
                    "years_experience": p.years_experience,
                    "photo_url": p.photo_url,
                    "location": p.location,
                    "languages": p.languages,
                    "match_score": int(round(min(0.99, max(0.35, score)) * 100)),
                    "similar_cases": [c.diagnosis for c in pcases if sims.get(c.id, 0) >= RELEVANT_CASE_SIM][:3],
                    "next_available": nxt.isoformat() if nxt else None,
                    "reason": "",
                }
            )

    reasons: dict[int, str] = {}
    if recs and not settings.demo_mode:
        try:
            doctors = "\n".join(
                f"provider_id={r['provider_id']}: {r['name']} ({r['specialty']}, {r['years_experience']} yrs, rating {r['rating']}); "
                f"similar past cases: {', '.join(r['similar_cases']) or 'general'}; next available: {r['next_available']}"
                for r in recs
            )
            out = invoke_structured(ProviderReasons, 
                [SystemMessage(MATCHER_SYSTEM), HumanMessage(f"Patient summary: {summary}\n\nCandidates:\n{doctors}")]
            )
            reasons = {i.provider_id: i.reason for i in out.items}
        except Exception:
            log.exception("Matcher LLM failed; using template reasons")
    for r in recs:
        if r["provider_id"] in reasons:
            r["reason"] = reasons[r["provider_id"]]
        elif r["similar_cases"]:
            r["reason"] = f"Has treated patients with similar symptoms (e.g. {r['similar_cases'][0].lower()}) — {r['years_experience']} years of experience."
        else:
            r["reason"] = f"Highly rated {r['specialty']} specialist with {r['years_experience']} years of experience."

    text = (
        f"Here are the top {len(recs)} doctors I matched for you, based on patients they've successfully treated with similar symptoms, "
        "their ratings and how soon they can see you. Select a doctor to view open slots and book."
        if recs
        else "I couldn't find an available provider for this specialty right now. Please try again later or contact our clinic."
    )
    return {
        "recommendations": recs,
        "messages": [_ai(text, {"type": "recommendations", "providers": recs, "specialty": specialty})],
        "trace": _trace(state, "match_providers"),
        "phase": "recommended",
    }


def summarize_memory(state: HealthState) -> dict:
    cls = state.get("classification") or {}
    with SessionLocal() as db:
        db.add(
            ConsultationSummary(
                patient_id=state["patient_id"],
                conversation_id=state.get("conversation_id"),
                summary=state.get("symptom_summary", "")[:2000],
                specialty=cls.get("specialty"),
                urgency=cls.get("urgency"),
            )
        )
        db.commit()
    return {"trace": _trace(state, "summarize_memory")}


def concierge(state: HealthState) -> dict:
    msgs = state.get("messages", [])
    latest = msgs[-1].content if msgs else ""
    cls = state.get("classification") or {}
    decision: ConciergeDecision | None = None
    if not settings.demo_mode:
        try:
            doctors = ", ".join(f"{r['name']} ({r['specialty']}, next: {r['next_available']})" for r in state.get("recommendations", []))
            system = CONCIERGE_SYSTEM.format(
                safety=SAFETY_POLICY,
                specialty=cls.get("specialty"),
                urgency=cls.get("urgency"),
                summary=state.get("symptom_summary", ""),
                doctors=doctors,
                patient_context=state.get("patient_context", ""),
            )
            decision = invoke_structured(ConciergeDecision, [SystemMessage(system), *_chat_history(msgs)[-12:]])
        except Exception:
            log.exception("Concierge LLM failed; using fallback")
    if decision is None:
        decision = fallback.concierge(latest)
    if fallback.detect_red_flag(latest):
        decision.intent = "new_symptoms"

    if decision.intent == "new_symptoms":
        return {
            "messages": [_ai(decision.reply, {"type": "new_assessment"}, assessment_start=True)],
            "phase": "intake",
            "followup_count": 0,
            "classification": None,
            "recommendations": [],
            "emergency": None,
            "symptom_summary": "",
            "_concierge_intent": "new_symptoms",
            "trace": _trace(state, "concierge"),
        }
    return {"messages": [_ai(decision.reply)], "_concierge_intent": "question", "trace": _trace(state, "concierge")}


# ───────────────────────── routing ─────────────────────────

def route_entry(state: HealthState) -> str:
    return "concierge" if state.get("phase") == "recommended" else "intake_agent"


def route_intake(state: HealthState) -> str:
    return {"ask": END, "emergency": "emergency"}.get(state.get("_intake_action", "complete"), "classify_specialty")


def route_concierge(state: HealthState) -> str:
    return "intake_agent" if state.get("_concierge_intent") == "new_symptoms" else END


def build_graph(checkpointer=None):
    g = StateGraph(HealthState)
    g.add_node("load_context", load_context)
    g.add_node("intake_agent", intake_agent)
    g.add_node("emergency", emergency)
    g.add_node("classify_specialty", classify_specialty)
    g.add_node("match_providers", match_providers)
    g.add_node("summarize_memory", summarize_memory)
    g.add_node("concierge", concierge)

    g.add_edge(START, "load_context")
    g.add_conditional_edges("load_context", route_entry, ["intake_agent", "concierge"])
    g.add_conditional_edges("intake_agent", route_intake, [END, "emergency", "classify_specialty"])
    g.add_edge("emergency", "classify_specialty")
    g.add_edge("classify_specialty", "match_providers")
    g.add_edge("match_providers", "summarize_memory")
    g.add_edge("summarize_memory", END)
    g.add_conditional_edges("concierge", route_concierge, ["intake_agent", END])
    return g.compile(checkpointer=checkpointer)


# ───────────────────────── checkpointer / singleton ─────────────────────────

_graph = None


def _make_checkpointer():
    if settings.is_postgres:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row

        conn = psycopg.Connection.connect(settings.postgres_dsn, autocommit=True, prepare_threshold=0, row_factory=dict_row)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver

    Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph(_make_checkpointer())
    return _graph
