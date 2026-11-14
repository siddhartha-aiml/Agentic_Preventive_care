"""Deterministic rule-based agents used in demo mode (no OPENAI_API_KEY) and in tests."""

import re

from . import i18n
from .llm import ConciergeDecision, IntakeDecision, SpecialtyClassification
from .specialties import RED_FLAGS, SPECIALTIES

GREETINGS = {"hi", "hello", "hey", "hii", "good morning", "good evening", "good afternoon", "yo", "namaste", "namaskar"}
GREETINGS_HI = {"नमस्ते", "नमस्कार", "हेलो", "हैलो", "हाय", "प्रणाम"}


def detect_red_flag(text: str) -> str:
    t = text.lower()
    for phrase in RED_FLAGS:
        if phrase in t:
            return phrase
    return i18n.detect_hindi_red_flag(text)


def _is_greeting(text: str) -> bool:
    if re.sub(r"[^a-z ]", "", text.lower()).strip() in GREETINGS:
        return True
    return re.sub(r"[^\u0900-\u097f ]", "", text).strip() in GREETINGS_HI


def intake(user_texts: list[str], followup_count: int, max_followups: int, patient_context: str, language: str = "en-IN") -> IntakeDecision:
    latest = user_texts[-1] if user_texts else ""
    said = " ".join(user_texts)
    flag = detect_red_flag(said)
    if flag:
        return IntakeDecision(
            red_flag=True,
            red_flag_reason=i18n.t("rule_flag", language, flag=flag),
            action="complete",
            question=i18n.t("fb_red_flag", language),
            symptom_summary=_summary(said),
        )
    if len(user_texts) == 1 and _is_greeting(latest):
        return IntakeDecision(red_flag=False, red_flag_reason="", action="ask", question=i18n.t("fb_greeting", language), symptom_summary="")

    has_history = "Known conditions: none recorded" not in patient_context
    conditions = ""
    for line in patient_context.splitlines():
        if line.startswith("Known conditions:"):
            conditions = line.split(":", 1)[1].strip()
    questions = [
        i18n.t("fb_q1", language),
        i18n.t("fb_q2", language),
        i18n.t("fb_q3_history", language, conditions=conditions) if has_history else i18n.t("fb_q3", language),
    ]
    limit = min(max_followups, len(questions))
    if followup_count < limit:
        return IntakeDecision(red_flag=False, red_flag_reason="", action="ask", question=questions[followup_count], symptom_summary="")
    return IntakeDecision(
        red_flag=False, red_flag_reason="", action="complete",
        question=i18n.t("fb_complete", language),
        symptom_summary=_summary(" | ".join(t for t in user_texts if not _is_greeting(t)), prefix="Patient reports: "),
    )


def _summary(text: str, prefix: str = "") -> str:
    """Keep the patient's own words and add English keywords so the doctor and the case matcher can use them."""
    english = i18n.gloss(text)
    return f"{prefix}{text}" + (f" [English keywords: {english}]" if english else "")


def classify(text: str, emergency: bool, language: str = "en-IN") -> SpecialtyClassification:
    t = (text + " " + i18n.gloss(text)).lower()
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
        reasoning=i18n.t("fb_reasoning", language, specialty=best, desc=desc.lower()),
        title=f"{best} consultation",
    )


def concierge(latest: str, language: str = "en-IN") -> ConciergeDecision:
    t = latest.lower()
    new = (
        re.search(r"\b(also|another|new|different)\b.*\b(pain|ache|symptom|problem|issue|rash|fever)\b", t)
        or t.startswith("i have ")
        or re.search("(नई|नयी|दूसरी|एक और) (तकलीफ|परेशानी|दिक्कत|समस्या|बीमारी)", i18n._norm(latest))
    )
    if new:
        return ConciergeDecision(intent="new_symptoms", reply=i18n.t("fb_concierge_new", language))
    return ConciergeDecision(intent="question", reply=i18n.t("fb_concierge", language))
