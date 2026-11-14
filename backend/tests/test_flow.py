from app.db import SessionLocal
from app.models import Provider, User


def _new_conv(client, headers):
    r = client.post("/api/conversations", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _say(client, headers, conv_id, text):
    r = client.post(f"/api/conversations/{conv_id}/messages", headers=headers, json={"content": text})
    assert r.status_code == 200, r.text
    return r.json()


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert meta["demo_mode"] is True
    assert len(meta["specialties"]) == 13


def test_register_and_auth(client):
    r = client.post("/api/auth/register", json={"email": "new@x.com", "password": "secret12", "full_name": "New Person"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "patient"
    assert client.post("/api/auth/register", json={"email": "new@x.com", "password": "secret12", "full_name": "x"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "new@x.com", "password": "wrong"}).status_code == 401
    assert client.get("/api/conversations").status_code == 401


def test_full_intake_to_booking(client, patient_headers, login):
    conv = _new_conv(client, patient_headers)

    out = _say(client, patient_headers, conv, "I keep getting throbbing headaches on one side with nausea and sensitivity to light")
    assert out["state"]["phase"] == "intake"
    assert out["messages"][0]["payload"]["type"] == "followup"
    assert "intake_agent" in out["trace"]

    _say(client, patient_headers, conv, "About three weeks, they come on gradually")
    _say(client, patient_headers, conv, "Around 7 out of 10, they come and go")
    out = _say(client, patient_headers, conv, "Some dizziness, dark rooms help")

    assert out["trace"][-3:] == ["classify_specialty", "match_providers", "summarize_memory"]
    state = out["state"]
    assert state["phase"] == "recommended"
    assert state["classification"]["specialty"] == "Neurology"
    recs = state["recommendations"]
    assert 3 <= len(recs) <= 4
    assert all(r["specialty"] == "Neurology" for r in recs)
    assert recs[0]["specialty"] == "Neurology"
    assert out["conversation"]["specialty"] == "Neurology"

    # Conversation retained & reloadable
    detail = client.get(f"/api/conversations/{conv}", headers=patient_headers).json()
    assert detail["state"]["phase"] == "recommended"
    assert any(m["payload"] and m["payload"].get("type") == "recommendations" for m in detail["messages"])

    # Follow-up question goes to the concierge, not back to intake
    out = _say(client, patient_headers, conv, "What should I bring to the appointment?")
    assert out["trace"][-1] == "concierge"
    assert out["state"]["phase"] == "recommended"

    # Slots & booking
    pid = recs[0]["provider_id"]
    days = client.get(f"/api/providers/{pid}/slots", headers=patient_headers).json()
    assert days and days[0]["slots"]
    start = days[0]["slots"][0]["start"]
    r = client.post("/api/appointments", headers=patient_headers, json={"provider_id": pid, "start_time": start, "conversation_id": conv})
    assert r.status_code == 201, r.text
    appt = r.json()
    assert appt["ai_summary"]["specialty"] == "Neurology"

    # Double booking prevented and slot disappears
    r2 = client.post("/api/appointments", headers=patient_headers, json={"provider_id": pid, "start_time": start, "conversation_id": conv})
    assert r2.status_code == 409
    days_after = client.get(f"/api/providers/{pid}/slots", headers=patient_headers).json()
    assert start not in [s["start"] for d in days_after for s in d["slots"]]

    # Doctor sees it with AI summary
    with SessionLocal() as db:
        email = db.get(User, db.get(Provider, pid).user_id).email
    doc_headers = login(client, email, "doctor123")
    doc_appts = client.get("/api/doctor/appointments", headers=doc_headers).json()
    assert any(a["id"] == appt["id"] and a["ai_summary"]["symptom_summary"] for a in doc_appts)
    assert client.get("/api/doctor/appointments", headers=patient_headers).status_code == 403

    # Cancel frees the slot
    assert client.post(f"/api/appointments/{appt['id']}/cancel", headers=patient_headers).json()["status"] == "cancelled"
    days_after = client.get(f"/api/providers/{pid}/slots", headers=patient_headers).json()
    assert start in [s["start"] for d in days_after for s in d["slots"]]


def test_emergency_red_flag(client, patient_headers):
    conv = _new_conv(client, patient_headers)
    out = _say(client, patient_headers, conv, "I have crushing chest pain spreading to my left arm and I'm sweating")
    types = [m["payload"]["type"] for m in out["messages"] if m["payload"]]
    assert types[0] == "emergency"
    assert out["state"]["classification"]["urgency"] == "emergency"
    assert out["state"]["classification"]["specialty"] == "Cardiology"


def test_long_term_memory_used_in_new_conversation(client, patient_headers):
    from app.agents.graph import get_graph

    conv = _new_conv(client, patient_headers)
    _say(client, patient_headers, conv, "My skin is itchy with a red rash")
    values = get_graph().get_state({"configurable": {"thread_id": conv}}).values
    assert "Previous consultations (most recent first)" in values["patient_context"]
    assert "Hypertension" in values["patient_context"]


def test_conversation_isolation(client, patient_headers):
    conv = _new_conv(client, patient_headers)
    r = client.post("/api/auth/register", json={"email": "other@x.com", "password": "secret12", "full_name": "Other"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"/api/conversations/{conv}", headers=other).status_code == 404
    assert client.post(f"/api/conversations/{conv}/messages", headers=other, json={"content": "hi"}).status_code == 404
