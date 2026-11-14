"""Speech-to-text and text-to-speech through Sarvam AI (https://docs.sarvam.ai).

STT: POST {base}/speech-to-text   multipart: file, model=saaras:v3, mode=transcribe, language_code
TTS: POST {base}/text-to-speech   json: text, target_language_code, model=bulbul:v3, speaker → {"audios": [base64 wav]}
Auth for both: header `api-subscription-key`.
"""

import base64
import io
import logging
import re
import wave

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

TTS_CHUNK_CHARS = 900  # stay well inside the per-request text limit
STT_TIMEOUT = httpx.Timeout(45.0, connect=10.0)
TTS_TIMEOUT = httpx.Timeout(45.0, connect=10.0)


class SpeechError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict:
    if not settings.voice_enabled:
        raise SpeechError("Voice is not configured (SARVAM_API_KEY is missing).", 503)
    return {"api-subscription-key": settings.sarvam_api_key}


def _raise_for(resp: httpx.Response, what: str) -> None:
    if resp.status_code < 400:
        return
    log.error("Sarvam %s failed: %s %s", what, resp.status_code, resp.text[:500])
    if resp.status_code in (401, 403):
        raise SpeechError("The Sarvam API key was rejected. Check SARVAM_API_KEY.", 502)
    if resp.status_code == 429:
        raise SpeechError("Sarvam rate limit or credits exhausted. Try again shortly.", 503)
    raise SpeechError(f"Sarvam {what} failed ({resp.status_code}).", 502)


async def transcribe(audio: bytes, filename: str, content_type: str, language: str | None) -> dict:
    """Return {"transcript": str, "language_code": str}. `language=None` lets Sarvam detect the language."""
    data = {"model": settings.sarvam_stt_model, "mode": "transcribe", "language_code": language or "unknown"}
    files = {"file": (filename or "speech.wav", audio, content_type or "audio/wav")}
    try:
        async with httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
            resp = await client.post(f"{settings.sarvam_base_url}/speech-to-text", headers=_headers(), data=data, files=files)
    except httpx.HTTPError as exc:
        log.exception("Sarvam speech-to-text unreachable")
        raise SpeechError("Could not reach the speech service. Check your internet connection.") from exc
    _raise_for(resp, "speech-to-text")
    body = resp.json()
    return {"transcript": (body.get("transcript") or "").strip(), "language_code": body.get("language_code") or language}


def split_for_tts(text: str, limit: int = TTS_CHUNK_CHARS) -> list[str]:
    """Split on sentence ends (including the Hindi danda) so every request stays under the limit."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return [text] if text else []
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?।])\s+", text):
        while len(sentence) > limit:  # a single very long sentence: cut at a space
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            chunks.append(sentence[:cut])
            sentence = sentence[cut:].strip()
        if len(current) + len(sentence) + 1 > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return [c for c in chunks if c]


def join_wavs(parts: list[bytes]) -> bytes:
    if len(parts) == 1:
        return parts[0]
    out = io.BytesIO()
    writer = None
    for part in parts:
        with wave.open(io.BytesIO(part), "rb") as reader:
            if writer is None:
                writer = wave.open(out, "wb")
                writer.setparams(reader.getparams())
            writer.writeframes(reader.readframes(reader.getnframes()))
    if writer:
        writer.close()
    return out.getvalue()


async def synthesize(text: str, language: str) -> bytes:
    """Return WAV bytes of `text` spoken in `language` (BCP-47, e.g. hi-IN)."""
    chunks = split_for_tts(text)
    if not chunks:
        raise SpeechError("Nothing to speak.", 400)
    headers = _headers()
    parts: list[bytes] = []
    try:
        async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
            for chunk in chunks:
                resp = await client.post(
                    f"{settings.sarvam_base_url}/text-to-speech",
                    headers=headers,
                    json={
                        "text": chunk,
                        "target_language_code": language,
                        "model": settings.sarvam_tts_model,
                        "speaker": settings.sarvam_tts_speaker,
                        "pace": settings.sarvam_tts_pace,
                    },
                )
                _raise_for(resp, "text-to-speech")
                audios = resp.json().get("audios") or []
                if not audios:
                    raise SpeechError("Sarvam text-to-speech returned no audio.")
                parts.append(base64.b64decode("".join(audios)))
    except httpx.HTTPError as exc:
        log.exception("Sarvam text-to-speech unreachable")
        raise SpeechError("Could not reach the speech service. Check your internet connection.") from exc
    return join_wavs(parts)
