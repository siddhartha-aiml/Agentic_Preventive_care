# Your Health Guide 🩺

Agentic preventive-care portal for patients and doctors. Patients describe symptoms to an AI agent, which asks
follow-up questions, considers their medical history, classifies the right specialty, recommends the best-matched
doctors (based on cases they've treated before), and books an appointment in an open slot.

- **Orchestrator:** LangGraph (`backend/app/agents/graph.py`), persisted per conversation with a checkpointer
- **LLMs:** OpenAI GPT via `langchain-openai` (structured outputs) + OpenAI embeddings for case similarity
- **Backend:** FastAPI + SQLAlchemy (SQLite by default, Postgres optional)
- **Frontend:** React + Vite + TypeScript + Tailwind v4 + Framer Motion
- **Deploy:** single Docker image on Fly.io with a persistent volume

See **[SPEC.md](SPEC.md)** for the full specification and architecture.

```
START → load_context ─┬─ intake ─► intake_agent ─┬─ ask follow-up ─► END (wait for patient)
                      │                           ├─ red flag ─► emergency ─┐
                      │                           └─ complete ──────────────┴► classify_specialty
                      │                                 → match_providers → summarize_memory → END
                      └─ recommended ─► concierge ─┬─ question ─► END
                                                   └─ new symptoms ─► intake_agent
```

## Voice pilot (Sarvam AI)

Patients can talk to the agent in their own language instead of typing. Hindi is the first-class language; ten more
Indian languages are selectable.

```
mic (browser, 16 kHz WAV) → POST /api/voice/transcribe → Sarvam Saaras (speech → text, native script)
        → POST /api/conversations/{id}/messages {content, language}   ← the same LangGraph flow as typed chat
        → every assistant message carries payload.speech (plain, read-aloud text in the patient's language)
        → POST /api/voice/speak → Sarvam Bulbul (text → speech) → played automatically
```

- **Set `SARVAM_API_KEY`** in `.env` to turn Sarvam on. Without it the app falls back to the browser's built-in
  speech recognition and voices (Chrome / Edge), so the flow can be tried before the key arrives.
- **Language handling:** with an OpenAI key the agents answer directly in the patient's language (simple spoken
  words, no markdown); the symptom summary for the doctor is always written in English. Without an OpenAI key
  (demo mode) Hindi works through hand-written prompts and a Hindi→English symptom glossary
  (`backend/app/agents/i18n.py`); other languages get English replies.
- **Safety:** emergency phrases are also detected in Hindi (Devanagari and romanised), independent of the model.
- **Matching:** doctors who speak the patient's language get a small boost on top of the similar-case score.
- **Mock data:** `backend/app/seed_india.py` adds 25 Hindi-speaking doctors (Shamli, Muzaffarnagar, Meerut, …)
  with cases common in Indian clinics, plus a Hindi demo patient: `ramesh@demo.com` / `demo1234`. It is additive,
  so an existing database picks the new doctors up on the next start.
- **Limits of the pilot:** recordings are capped at 28 seconds per turn (synchronous speech-to-text); booking
  still needs a tap on the doctor card; login is still e-mail + password.

Key files: `backend/app/services/speech.py`, `backend/app/routers/voice.py`, `backend/app/agents/i18n.py`,
`frontend/src/lib/voice.ts`, `frontend/src/components/VoiceBar.tsx`.

## Run locally

```bash
# 1. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env            # add OPENAI_API_KEY and SARVAM_API_KEY (both optional: empty = demo mode / browser voice)
cd backend && uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend && npm install && npm run dev     # http://localhost:5173 (proxies /api → :8000)
```

**No API key?** The app runs in *demo mode*: rule-based agents (keyword triage, scripted follow-ups, lexical
similarity) stand in for GPT, so the whole flow still works. A banner in the portal tells you when demo mode is on.

### Demo accounts (seeded on first start)
| Role | Login |
|---|---|
| Patient | `patient@demo.com` / `demo1234` (has hypertension + type 2 diabetes in their history) |
| Doctors | pick any from the dropdown on the login page's **Doctor** tab, password `doctor123` |

Set `SHOW_DEMO_ACCOUNTS=false` to hide the demo logins in production.

### Tests
```bash
cd backend && pytest -q        # runs fully offline in demo mode
```

## Deploy to Fly.io

```bash
fly launch --no-deploy                       # accept the Dockerfile; pick a unique app name
fly volumes create yhg_data --size 1         # same region as the app
fly secrets set OPENAI_API_KEY=sk-... JWT_SECRET=$(openssl rand -hex 32)
fly deploy
fly open
```

- SQLite lives on the `/data` volume, so run **one** machine (the default here).
- To scale out, create Fly Postgres (`fly postgres create` + `fly postgres attach`). This sets `DATABASE_URL`, and
  the app then uses Postgres for both app data and LangGraph checkpoints.
- Health check: `GET /api/health`. API docs: `/api/docs`.

## Project layout

```
backend/app/
  agents/        graph.py (LangGraph), prompts.py, llm.py (schemas), fallback.py (demo mode), specialties.py
  routers/       auth, conversations (chat), providers (slots), appointments, patients, doctor
  services/      scheduling.py (slot generation, safe booking), similarity.py (embeddings / lexical)
  models.py      SQLAlchemy models    seed.py   demo providers, cases, schedules, patient
frontend/src/
  pages/         Landing, Auth, Workspace (sidebar), Chat, Appointments, Profile, Doctor
  components/    ChatParts (messages, provider cards, agent activity), SlotPicker, Logo, Avatar
```

## Disclaimer
Your Health Guide provides triage and booking guidance, not a medical diagnosis. A real deployment that handles
PHI needs HIPAA-grade controls: BAAs with OpenAI and your hosting provider, audit logging, and a security review.

Photos: Unsplash (free licence). Demo doctor portraits: randomuser.me.
