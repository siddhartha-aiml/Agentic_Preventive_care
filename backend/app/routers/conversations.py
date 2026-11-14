import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from ..agents.graph import get_graph
from ..config import get_settings
from ..db import get_db
from ..models import Conversation, Message, Patient, utcnow
from ..schemas import ConversationDetail, ConversationOut, MessageOut, SendMessageIn, SendMessageOut
from ..security import get_current_patient

router = APIRouter(prefix="/conversations", tags=["conversations"])
log = logging.getLogger(__name__)
settings = get_settings()


def _config(conv_id: str) -> dict:
    return {"configurable": {"thread_id": conv_id}}


def graph_state(conv_id: str) -> dict:
    values = get_graph().get_state(_config(conv_id)).values or {}
    return {
        "phase": values.get("phase", "intake"),
        "followup_count": values.get("followup_count", 0),
        "max_followups": settings.max_followups,
        "classification": values.get("classification"),
        "recommendations": values.get("recommendations", []),
        "emergency": values.get("emergency"),
        "symptom_summary": values.get("symptom_summary", ""),
    }


def _get_conv(db: Session, conv_id: str, patient: Patient) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if not conv or conv.patient_id != patient.id:
        raise HTTPException(404, "Conversation not found")
    return conv


def _greeting(patient: Patient) -> str:
    first = patient.user.full_name.split()[0]
    known = [c.split("(")[0].strip() for c in (patient.conditions or [])][:3]
    history = (
        f" I can see your health profile (including {', '.join(known)}) and I'll take it into account."
        if known
        else " If you have any existing conditions, you can add them in your Health Profile so I can take them into account."
    )
    return (
        f"Hi {first} 👋 I'm your **Health Guide**.{history}\n\n"
        "Tell me what's been bothering you — what symptoms are you experiencing, and when did they start? "
        "I'll ask a few follow-up questions, figure out which specialist fits best, and help you book an appointment."
    )


@router.get("", response_model=list[ConversationOut])
def list_conversations(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.patient_id == patient.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=ConversationDetail, status_code=201)
def create_conversation(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    conv = Conversation(patient_id=patient.id)
    db.add(conv)
    db.flush()
    db.add(Message(conversation_id=conv.id, role="assistant", content=_greeting(patient), payload={"type": "greeting"}))
    db.commit()
    db.refresh(conv)
    return ConversationDetail(
        **ConversationOut.model_validate(conv).model_dump(),
        messages=[MessageOut.model_validate(m) for m in conv.messages],
        state=graph_state(conv.id),
    )


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    conv = _get_conv(db, conv_id, patient)
    return ConversationDetail(
        **ConversationOut.model_validate(conv).model_dump(),
        messages=[MessageOut.model_validate(m) for m in conv.messages],
        state=graph_state(conv.id),
    )


@router.delete("/{conv_id}", status_code=204)
def delete_conversation(conv_id: str, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    conv = _get_conv(db, conv_id, patient)
    db.delete(conv)
    db.commit()
    try:
        get_graph().checkpointer.delete_thread(conv_id)
    except Exception:
        log.warning("Could not delete checkpoint thread %s", conv_id)


@router.post("/{conv_id}/messages", response_model=SendMessageOut)
async def send_message(
    conv_id: str, body: SendMessageIn, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
):
    conv = _get_conv(db, conv_id, patient)
    text = body.content.strip()
    graph = get_graph()
    config = _config(conv.id)

    snapshot = await run_in_threadpool(graph.get_state, config)
    prior = snapshot.values.get("messages", []) if snapshot.values else []
    inputs: dict = {"patient_id": patient.id, "conversation_id": conv.id, "messages": [HumanMessage(text)]}
    if not prior:
        greeting = next((m.content for m in conv.messages if m.role == "assistant"), _greeting(patient))
        inputs["messages"] = [AIMessage(greeting), HumanMessage(text)]
        inputs.update(phase="intake", followup_count=0)
    before = len(prior) + len(inputs["messages"])

    user_msg = Message(conversation_id=conv.id, role="user", content=text)
    db.add(user_msg)
    db.commit()

    try:
        result = await run_in_threadpool(graph.invoke, inputs, config)
    except Exception:
        log.exception("Graph execution failed")
        raise HTTPException(502, "The health assistant is temporarily unavailable. Please try again.")

    new_msgs = []
    for m in result["messages"][before:]:
        if isinstance(m, AIMessage) and m.content:
            row = Message(conversation_id=conv.id, role="assistant", content=m.content, payload=m.additional_kwargs.get("payload"))
            db.add(row)
            new_msgs.append(row)

    cls = result.get("classification") or {}
    conv.phase = result.get("phase", conv.phase)
    if cls:
        if cls.get("title") and cls.get("specialty") != conv.specialty:
            conv.title = cls["title"][:255]
        conv.specialty = cls.get("specialty")
        conv.urgency = cls.get("urgency")
    if conv.title == "New consultation":
        conv.title = (text[:60] + "…") if len(text) > 60 else text
    conv.updated_at = utcnow()
    db.commit()
    for m in new_msgs:
        db.refresh(m)
    db.refresh(conv)

    return SendMessageOut(
        messages=[MessageOut.model_validate(m) for m in new_msgs],
        state=graph_state(conv.id),
        trace=result.get("trace", []),
        conversation=ConversationOut.model_validate(conv),
    )
