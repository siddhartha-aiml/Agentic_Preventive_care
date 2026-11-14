"""Deterministic rule-based agents used in demo mode (no OPENAI_API_KEY) and in tests."""

import re

from .llm import ConciergeDecision, IntakeDecision, SpecialtyClassification
from .specialties import RED_FLAGS, SPECIALTIES

GREETINGS = {"hi", "hello", "hey", "hii", "good morning", "good evening", "good afternoon", "yo"}


def detect_red_flag(text: str) -> str:
    t = text.lower()
    for phrase in RED_FLAGS:
        if phrase in t:
            return phrase
    return ""


def _is_greeting(text: str) -> bool:
    return re.sub(r"[^a-z ]", "", text.lower()).strip() in GREETINGS


def intake(user_texts: list[str], followup_count: int, max_followups: int, patient_context: str) -> IntakeDecision:
    latest = user_texts[-1] if user_texts else ""
    flag = detect_red_flag(" ".join(user_texts))
    if flag:
        return IntakeDecision(
            red_flag=True,
            red_flag_reason=f"You mentioned “{flag}”, which can be a sign of a medical emergency.",
            action="complete",
            question="I'm flagging this as potentially urgent.",
            symptom_summary=" ".join(user_texts),
        )
    if len(user_texts) == 1 and _is_greeting(latest):
        return IntakeDecision(
            red_flag=False, red_flag_reason="", action="ask",
            question="Hello! 😊 What symptoms or health concerns brought you here today?",
            symptom_summary="",
        )

    has_history = "Known conditions: none recorded" not in patient_context
    conditions = ""
    for line in patient_context.splitlines():
        if line.startswith("Known conditions:"):
            conditions = line.split(":", 1)[1].strip()
    questions = [
        "Thanks for sharing that. How long have you had these symptoms, and did they start suddenly or gradually?",
        "On a scale of 1 to 10, how severe is it right now — and is it constant, or does it come and go?",
        (
            f"Given your history ({conditions}), have you noticed any related changes recently? "
            "Also, are there other symptoms — such as fever, nausea, dizziness or shortness of breath — or anything that makes it better or worse?"
            if has_history
            else "Are there any other symptoms — such as fever, nausea, dizziness or shortness of breath — or anything that makes it better or worse?"
        ),
    ]
    limit = min(max_followups, len(questions))
    if followup_count < limit:
        return IntakeDecision(red_flag=False, red_flag_reason="", action="ask", question=questions[followup_count], symptom_summary="")
    return IntakeDecision(
        red_flag=False, red_flag_reason="", action="complete",
        question="Thank you — I have a clear picture now. Let me find the right specialist for you.",
        symptom_summary="Patient reports: " + " | ".join(t for t in user_texts if not _is_greeting(t)),
    )


def classify(text: str, emergency: bool) -> SpecialtyClassification:
    t = text.lower()
    scores = {name: sum(t.count(k) for k in info["keywords"]) for name, info in SPECIALTIES.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, best_score = ranked[0]
    second = ranked[1][0] if ranked[1][1] > 0 else "General Physician"
    if best_score == 0:
        best, second = "General Physician", "General Physician"
    total = sum(scores.values()) or 1
    confidence = round(min(0.95, 0.45 + 0.5 * best_score / total), 2) if best_score else 0.4

    if emergency:
        urgency = "emergency"
    elif re.search(r"\b(9|10)\s*(/|out of)\s*10\b|severe|unbearable|getting worse|worsening", t):
        urgency = "urgent"
    elif re.search(r"\b(7|8)\s*(/|out of)\s*10\b|sudden|days", t):
        urgency = "soon"
    else:
        urgency = "routine"
    desc = SPECIALTIES[best]["description"].split(":")[0]
    return SpecialtyClassification(
        specialty=best,
        secondary_specialty=second,
        confidence=confidence,
        urgency=urgency,
        reasoning=f"Your symptoms are commonly evaluated by a {best} specialist ({desc.lower()}).",
        title=f"{best} consultation",
    )


def concierge(latest: str) -> ConciergeDecision:
    t = latest.lower()
    new = re.search(r"\b(also|another|new|different)\b.*\b(pain|ache|symptom|problem|issue|rash|fever)\b", t) or t.startswith("i have ")
    if new:
        return ConciergeDecision(intent="new_symptoms", reply="Let's look at that new concern — I'll start a fresh assessment.")
    return ConciergeDecision(
        intent="question",
        reply=(
            "Happy to help! Tap any doctor card above to see their open slots and book instantly. "
            "Bring a list of your current medications and note when your symptoms started — it helps your doctor a lot. "
            "If your symptoms suddenly worsen, please seek urgent care."
        ),
    )
