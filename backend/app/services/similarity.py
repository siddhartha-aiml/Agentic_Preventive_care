"""Case-similarity scoring: OpenAI embeddings (cached in DB) with a lexical fallback for demo mode."""

import logging
import math
import re
from collections import Counter

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ProviderCase

log = logging.getLogger(__name__)
settings = get_settings()

_STOP = set(
    "a an the and or of in on at to for with without my i me is are was were be been have has had it its this that "
    "since from by as after before when while very some few days day weeks week months month years year".split()
)


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    out = []
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        out.append(w[:6])  # crude stemming: "headaches" ~ "headac" ~ "headache"
    return out


def lexical_similarity(a: str, b: str) -> float:
    ta, tb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ta or not tb:
        return 0.0
    dot = sum(ta[t] * tb[t] for t in ta)
    return dot / (math.sqrt(sum(v * v for v in ta.values())) * math.sqrt(sum(v * v for v in tb.values())))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _embedder():
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key)


def ensure_case_embeddings(db: Session, cases: list[ProviderCase]) -> None:
    missing = [c for c in cases if not c.embedding]
    if not missing:
        return
    vectors = _embedder().embed_documents([f"{c.symptoms}. Diagnosis: {c.diagnosis}" for c in missing])
    for c, v in zip(missing, vectors):
        c.embedding = v
    db.commit()


def score_cases(db: Session, query: str, cases: list[ProviderCase]) -> dict[int, float]:
    """Return {case_id: similarity in [0,1]}."""
    if not cases:
        return {}
    if not settings.demo_mode:
        try:
            ensure_case_embeddings(db, cases)
            qv = _embedder().embed_query(query)
            # text-embedding-3 cosine for related clinical text sits ~0.2-0.7; rescale to [0,1].
            return {c.id: max(0.0, min(1.0, (_cosine(qv, c.embedding) - 0.15) / 0.55)) for c in cases}
        except Exception as exc:  # network/quota issues should not break matching
            from ..agents.llm import record_llm_error

            record_llm_error(exc)
            log.exception("Embedding similarity failed; falling back to lexical")
    return {c.id: min(1.0, lexical_similarity(query, f"{c.symptoms} {c.diagnosis}") * 1.6) for c in cases}
