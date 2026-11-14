"""Voice endpoints: speech in (Sarvam Saaras) and speech out (Sarvam Bulbul)."""

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..agents.i18n import DEFAULT_LANGUAGE, LANGUAGES, normalize_language
from ..config import get_settings
from ..models import User
from ..security import get_current_user
from ..services import speech

router = APIRouter(prefix="/voice", tags=["voice"])
settings = get_settings()


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = DEFAULT_LANGUAGE


@router.get("/config")
def voice_config():
    """What the client needs to draw the voice bar. `provider` is "browser" until SARVAM_API_KEY is set."""
    return {
        "provider": "sarvam" if settings.voice_enabled else "browser",
        "default_language": "hi-IN",
        "max_seconds": 28,  # Sarvam's synchronous speech-to-text endpoint takes short clips
        "languages": [{"code": code, **info} for code, info in LANGUAGES.items()],
    }


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("auto"), _: User = Depends(get_current_user)):
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "The recording was empty.")
    if len(audio) > settings.voice_max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "The recording is too long. Please speak for less than 30 seconds.")
    lang = None if language in ("auto", "unknown", "") else normalize_language(language)
    try:
        result = await speech.transcribe(audio, file.filename or "speech.wav", file.content_type or "audio/wav", lang)
    except speech.SpeechError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    if not result["transcript"]:
        raise HTTPException(422, "I could not hear anything. Please try again.")
    result["language_code"] = normalize_language(result["language_code"]) if result["language_code"] in LANGUAGES else (lang or DEFAULT_LANGUAGE)
    return result


@router.post("/speak")
async def speak(body: SpeakIn, _: User = Depends(get_current_user)):
    try:
        wav = await speech.synthesize(body.text, normalize_language(body.language))
    except speech.SpeechError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return {"mime": "audio/wav", "audio_base64": base64.b64encode(wav).decode()}
