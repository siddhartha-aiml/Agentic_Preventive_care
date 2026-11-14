"""Voice layer and Hindi flow. Runs offline: Sarvam calls are mocked, agents run in rule-based demo mode."""

import base64
import io
import wave

import httpx
import pytest

from app.agents import fallback, i18n
from app.services import speech


def _wav(seconds: float = 0.1, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


def _new_conv(client, headers, language=None):
    r = client.post("/api/conversations", headers=headers, params={"language": language} if language else None)
    assert r.status_code == 201, r.text
    return r.json()


def _say(client, headers, conv_id, text, language=None):
    body = {"content": text, **({"language": language} if language else {})}
    r = client.post(f"/api/conversations/{conv_id}/messages", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_voice_config_and_browser_fallback_without_key(client, patient_headers):
    cfg = client.get("/api/voice/config").json()
    assert cfg["provider"] == "browser"
    assert {"hi-IN", "en-IN"} <= {lang["code"] for lang in cfg["languages"]}
    assert client.get("/api/meta").json()["voice_provider"] == "browser"
    r = client.post("/api/voice/speak", headers=patient_headers, json={"text": "नमस्ते", "language": "hi-IN"})
    assert r.status_code == 503
    r = client.post("/api/voice/transcribe", headers=patient_headers, files={"file": ("a.wav", _wav(), "audio/wav")})
    assert r.status_code == 503
    assert client.post("/api/voice/speak", json={"text": "x"}).status_code == 401


def test_hindi_glossary_and_red_flags():
    assert "stomach" in i18n.gloss("मेरे पेट में दर्द है और उल्टी हो रही है")
    assert "headache" in i18n.gloss("सिर में दर्द रहता है")
    assert i18n.gloss("मेरी दुकान दिल्ली में है") == ""  # 'कान' inside 'दुकान' must not mean ear
    assert i18n.gloss("I bought a carpet") == ""
    assert fallback.detect_red_flag("मुझे साँस नहीं आ रही है")  # chandrabindu spelling variant
    assert fallback.detect_red_flag("सीने में बहुत दर्द हो रहा है")
    assert not fallback.detect_red_flag("हल्का बुखार है")
    assert fallback.classify("पेशाब में जलन और पथरी", False).specialty == "Urology"
    assert fallback.classify("घुटनों में दर्द है, सीढ़ी चढ़ने में दिक्कत", False).specialty == "Orthopedics"


def test_speech_text_is_plain_and_speaks_numbers():
    spoken = i18n.speech_text("⚠️ **अभी 112 पर फोन करें** या 108", {"type": "emergency"}, "hi-IN")
    assert "*" not in spoken and "⚠" not in spoken
    assert "एक एक दो" in spoken and "एक शून्य आठ" in spoken
    recs = {"type": "recommendations", "providers": [{"name": "Dr. Anjali Sharma", "reason": "अच्छे डॉक्टर हैं।"}]}
    assert "नंबर 1: डॉक्टर Anjali Sharma" in i18n.speech_text("डॉक्टर चुने हैं।", recs, "hi-IN")


def test_hindi_conversation_end_to_end(client, login):
    headers = login(client, "ramesh@demo.com", "demo1234")
    conv = _new_conv(client, headers, "hi-IN")
    greeting = conv["messages"][0]
    assert "नमस्ते Ramesh" in greeting["content"]
    assert greeting["payload"]["speech"] and "*" not in greeting["payload"]["speech"]

    out = _say(client, headers, conv["id"], "मेरे पेट में बहुत जलन होती है और गैस बनती है", "hi-IN")
    first = out["messages"][0]
    assert first["payload"]["type"] == "followup"
    assert "कितने दिनों" in first["content"]  # the follow-up is asked in Hindi
    assert first["payload"]["language"] == "hi-IN" and first["payload"]["speech"]
    assert out["state"]["language"] == "hi-IN"

    _say(client, headers, conv["id"], "दस दिन से, धीरे धीरे बढ़ा है")  # language is remembered
    _say(client, headers, conv["id"], "ज़्यादा है, खाने के बाद होता है")
    out = _say(client, headers, conv["id"], "कभी कभी उल्टी जैसा लगता है")

    state = out["state"]
    assert state["phase"] == "recommended"
    assert state["classification"]["specialty"] == "Gastroenterology"
    assert "English keywords" in state["symptom_summary"]  # the doctor gets English terms too
    recs = state["recommendations"]
    assert 3 <= len(recs) <= 4
    assert "Hindi" in recs[0]["languages"]
    assert any(r["similar_cases"] for r in recs)  # matched on cases they treated before
    spoken = next(m["payload"]["speech"] for m in out["messages"] if m["payload"]["type"] == "recommendations")
    assert "नंबर 1" in spoken


def test_hindi_emergency(client, login):
    headers = login(client, "ramesh@demo.com", "demo1234")
    conv = _new_conv(client, headers, "hi-IN")
    out = _say(client, headers, conv["id"], "सीने में बहुत दर्द हो रहा है और पसीना आ रहा है", "hi-IN")
    emergency = out["messages"][0]
    assert emergency["payload"]["type"] == "emergency"
    assert "112" in emergency["content"] and "एक एक दो" in emergency["payload"]["speech"]
    assert out["state"]["classification"]["urgency"] == "emergency"
    assert out["state"]["classification"]["specialty"] == "Cardiology"


def test_india_seed_is_idempotent(client):
    from app.db import SessionLocal
    from app.models import Provider
    from app.seed_india import INDIA_PROVIDERS, seed_india

    with SessionLocal() as db:
        before = db.query(Provider).count()
        assert seed_india(db) == 0
        assert db.query(Provider).count() == before
        assert db.query(Provider).filter(Provider.location.like("%Shamli%")).count() >= 3
        assert before >= len(INDIA_PROVIDERS)


def test_tts_chunking_and_wav_join():
    text = "यह एक वाक्य है। " * 200
    chunks = speech.split_for_tts(text)
    assert len(chunks) > 1 and all(len(c) <= speech.TTS_CHUNK_CHARS for c in chunks)
    joined = speech.join_wavs([_wav(0.1), _wav(0.2)])
    with wave.open(io.BytesIO(joined), "rb") as w:
        assert abs(w.getnframes() / w.getframerate() - 0.3) < 0.01


def test_sarvam_calls(client, patient_headers, monkeypatch):
    """With a key set, the endpoints call Sarvam with the documented request shape."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["api-subscription-key"] == "sk-sarvam-test"
        if request.url.path == "/speech-to-text":
            body = request.content
            assert b'name="model"' in body and b"saaras:v3" in body and b'name="file"' in body and b"hi-IN" in body
            return httpx.Response(200, json={"transcript": " पेट में दर्द है ", "language_code": "hi-IN"})
        if request.url.path == "/text-to-speech":
            import json

            payload = json.loads(request.content)
            assert payload["target_language_code"] == "hi-IN" and payload["model"] == "bulbul:v3" and payload["text"]
            return httpx.Response(200, json={"audios": [base64.b64encode(_wav()).decode()]})
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(speech.settings, "sarvam_api_key", "sk-sarvam-test")
    monkeypatch.setattr(speech.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))

    r = client.post("/api/voice/transcribe", headers=patient_headers, data={"language": "hi-IN"}, files={"file": ("a.wav", _wav(), "audio/wav")})
    assert r.status_code == 200, r.text
    assert r.json() == {"transcript": "पेट में दर्द है", "language_code": "hi-IN"}

    r = client.post("/api/voice/speak", headers=patient_headers, json={"text": "नमस्ते, आप कैसे हैं?", "language": "hi-IN"})
    assert r.status_code == 200, r.text
    assert base64.b64decode(r.json()["audio_base64"])[:4] == b"RIFF"
    assert client.get("/api/voice/config").json()["provider"] == "sarvam"
    assert [q.url.path for q in seen] == ["/speech-to-text", "/text-to-speech"]


@pytest.mark.parametrize("status,expected", [(403, 502), (429, 503)])
def test_sarvam_errors_are_reported(client, patient_headers, monkeypatch, status, expected):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(speech.settings, "sarvam_api_key", "bad")
    monkeypatch.setattr(speech.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json={})), **kw))
    r = client.post("/api/voice/speak", headers=patient_headers, json={"text": "hello", "language": "en-IN"})
    assert r.status_code == expected
