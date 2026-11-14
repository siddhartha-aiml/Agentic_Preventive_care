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

## Run locally

```bash
# 1. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env            # add OPENAI_API_KEY (or leave empty for demo mode)
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
