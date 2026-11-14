# Your Health Guide — Product & Technical Specification

> Agentic preventive-care portal for **patients** and **doctors**.
> A patient describes symptoms to an AI agent, which asks follow-up questions, takes the patient's medical
> history into account, classifies the right specialty, recommends the best-matched providers, and books an
> appointment in an open slot.

---

## 1. Goals

| # | Goal | Acceptance criteria |
|---|------|---------------------|
| G1 | Secure login | Patients can register and log in; doctors log in to a separate dashboard. JWT auth; passwords stored with bcrypt. |
| G2 | Conversational symptom intake | The **Intake Agent** asks 1–4 focused follow-up questions (onset, duration, severity, associated symptoms, triggers) before finishing. Never more than `MAX_FOLLOWUPS` (default 4). |
| G3 | History-aware | The agent loads the patient's stored medical history (conditions, medications, allergies, surgeries, family history) **and** summaries of previous consultations, and uses them in questions and classification. |
| G4 | Specialty classification | The **Specialty Classifier** maps the case to one of a fixed list of specialties (General Physician, Cardiology, Neurology, …) with confidence, urgency (`routine` / `soon` / `urgent` / `emergency`) and reasoning. |
| G5 | Safety | Red-flag symptoms (e.g. crushing chest pain, stroke signs, suicidal intent, severe bleeding) short-circuit to an **emergency notice** (India: call 112 / ambulance 108; mental health crisis: Tele-MANAS 14416). The system never gives a diagnosis; it states it is not medical advice. |
| G6 | Provider matching | The **Provider Matcher Agent** ranks providers of the chosen specialty by similarity of their **past treated cases** to the current symptoms, plus rating, experience and near-term availability, and returns the **top 3–4** with a one-line "why this doctor". |
| G7 | Booking | The patient selects a provider → open slots for the next 14 days are shown (generated from the doctor's weekly availability minus booked appointments) → patient books. Double-booking is impossible (DB unique constraint). |
| G8 | Memory | Every conversation is persisted (LangGraph checkpointer per thread + message log). Patients can reopen any past conversation from the sidebar and continue it. Completed consultations are summarised into long-term patient memory used by future consultations. |
| G9 | Doctor view | Doctors see their upcoming appointments with the AI pre-visit summary (symptoms, follow-up answers, specialty, urgency, relevant history). |
| G10 | Deployable on Fly.io | One Docker image (React build served by FastAPI), `fly.toml`, persistent volume for SQLite, health check, secrets via `fly secrets`. Optional Postgres via `DATABASE_URL`. |

### Non-goals (v1)
Payments/insurance, video visits, e-prescriptions, real EHR (FHIR) integration, SMS/email notifications, HIPAA certification (the architecture keeps PHI server-side, but a real deployment needs a BAA with OpenAI and Fly, audit logging and encryption review).

---

## 2. Architecture

```
┌──────────────────────── Fly.io Machine (single Docker image) ────────────────────────┐
│                                                                                       │
│  React (Vite, TS, Tailwind, Framer Motion) ── static build served by FastAPI          │
│                     │  /api/*  (JSON, JWT bearer)                                      │
│                     ▼                                                                 │
│  FastAPI ── routers: auth · chat · conversations · providers · appointments ·        │
│             patients · doctor                                                         │
│                     │                                                                 │
│                     ▼                                                                 │
│  LangGraph orchestrator (StateGraph, checkpointer = SqliteSaver | PostgresSaver)      │
│     load_context → router → intake_agent ─┬─(ask follow-up)──► END (wait for user)    │
│                                            ├─(red flag)───────► emergency ─► END      │
│                                            └─(complete)──► classify_specialty         │
│                                                              ─► match_providers       │
│                                                              ─► summarize_memory ─► END│
│     phase == "recommended" → concierge_agent (Q&A about results / restart) ─► END     │
│                     │                                                                 │
│                     ▼                                                                 │
│  SQLAlchemy  ──  SQLite on /data volume (default)  or  Postgres (DATABASE_URL)        │
│  OpenAI GPT (chat + structured output) · OpenAI embeddings (case similarity)          │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

* **Orchestrator:** LangGraph `StateGraph`. One graph invocation per user message; `thread_id` = conversation id. State is restored by the checkpointer, so the intake loop is naturally resumable across requests, reloads and server restarts.
* **LLMs:** `langchain-openai` `ChatOpenAI` (model from `OPENAI_MODEL`, default `gpt-4.1-mini`) with `with_structured_output(PydanticModel)` for every decision step; `OpenAIEmbeddings` (`text-embedding-3-small`) for case similarity.
* **Offline/demo mode:** if `OPENAI_API_KEY` is not set, deterministic rule-based fallbacks (keyword triage, scripted follow-ups, lexical similarity) keep the whole flow working for local dev, demos and tests. The UI shows a "demo mode" badge.

---

## 3. Agents (LangGraph nodes)

### 3.1 Graph state (`HealthState`)
| Field | Type | Notes |
|---|---|---|
| `messages` | `list[BaseMessage]` (add_messages reducer) | full chat transcript |
| `patient_id` | int | |
| `patient_context` | str | rendered medical history + past consultation summaries |
| `phase` | `intake` \| `recommended` \| `emergency` | |
| `followup_count` | int | follow-up questions asked so far |
| `symptom_summary` | str | clinical-style summary produced at end of intake |
| `classification` | dict | `{specialty, confidence, urgency, reasoning, secondary_specialty}` |
| `recommendations` | list[dict] | top providers with score + reason |
| `trace` | list[str] | nodes executed during *this* turn (shown in UI as agent activity) |

### 3.2 Nodes
1. **`load_context`** – reads patient profile, medical history and last 5 consultation summaries from DB → `patient_context`. Resets `trace`.
2. **`intake_agent`** (Agent 1 – Symptom Intake). Structured output `IntakeDecision{red_flag: bool, red_flag_reason, action: ask|complete, question, symptom_summary}`.
   * Asks one empathetic, specific question at a time; may reference history ("You mentioned hypertension — have you checked your blood pressure today?").
   * Forced to `complete` once `followup_count >= MAX_FOLLOWUPS`.
   * Must ask at least one follow-up unless the first message is already comprehensive.
3. **`emergency`** – returns emergency guidance, sets `phase=emergency`; booking is still offered (urgent care / GP) but the UI shows a red banner.
4. **`classify_specialty`** (Agent 1b). Structured output `SpecialtyClassification`. Specialty constrained to the enum in `specialties.py`. Low confidence (< 0.5) → General Physician.
5. **`match_providers`** (Agent 2 – Provider Matcher).
   * Candidate set = providers in the specialty (+ secondary specialty if < 4 found, + General Physician fallback).
   * For each candidate, similarity = max/mean of top-3 cosine similarities between the symptom summary embedding and the provider's **past case** embeddings (cached in DB).
   * `score = 0.60·similarity + 0.20·(rating/5) + 0.10·min(years/25,1) + 0.10·availability_soon` (availability_soon = has a slot within 3 days).
   * Top 4 → LLM writes a one-sentence personalised rationale for each (fallback: template using the most similar past case).
6. **`summarize_memory`** – writes `ConsultationSummary` (symptoms, specialty, urgency) to DB for long-term memory and sets conversation title/specialty.
7. **`concierge_agent`** – after recommendations, answers questions about the doctors/specialty, or if the user describes *new* symptoms, resets to `intake` (new assessment in the same thread).

### 3.3 Prompts
All prompts live in `backend/app/agents/prompts.py`. Every system prompt includes: role, the safety policy (no diagnosis, emergency escalation), the patient context, and output constraints.

---

## 4. Data model (SQLAlchemy)

| Table | Key columns |
|---|---|
| `users` | id, email (unique), password_hash, role (`patient`/`doctor`), full_name, created_at |
| `patients` | id, user_id → users, date_of_birth, sex, phone, conditions (JSON), medications (JSON), allergies (JSON), surgeries (JSON), family_history (JSON), notes |
| `providers` | id, user_id → users (nullable), name, specialty, title, years_experience, rating, reviews_count, bio, location, languages (JSON), photo_url, accepts_new |
| `provider_cases` | id, provider_id, symptoms (text), diagnosis, outcome, embedding (JSON, nullable) — *de-identified historical cases treated by the provider* |
| `availability` | id, provider_id, weekday (0=Mon), start_time, end_time, slot_minutes |
| `appointments` | id, patient_id, provider_id, conversation_id, start_time, end_time, status (`booked`/`cancelled`/`completed`), reason, ai_summary (JSON); **unique(provider_id, start_time)** for active bookings |
| `conversations` | id (uuid = LangGraph thread_id), patient_id, title, phase, specialty, urgency, created_at, updated_at |
| `messages` | id, conversation_id, role (`user`/`assistant`/`system`), content, payload (JSON — e.g. recommendations card), created_at |
| `consultation_summaries` | id, patient_id, conversation_id, summary, specialty, urgency, created_at |

Seed data (`app/seed.py`, idempotent, runs on startup when DB empty): 13 specialties × 2–3 providers (~32 doctors) each with 8–12 historical cases and a weekly schedule; one demo patient with history; doctor logins.

---

## 5. REST API (`/api`)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | patient sign-up → JWT |
| POST | `/auth/login` | email + password → JWT (+ role) |
| GET | `/auth/me` | current user |
| GET/PUT | `/patients/me` | profile & medical history |
| GET | `/conversations` | list patient's conversations |
| POST | `/conversations` | create a new conversation (returns greeting) |
| GET | `/conversations/{id}` | messages + state (phase, classification, recommendations) |
| DELETE | `/conversations/{id}` | delete conversation |
| POST | `/conversations/{id}/messages` | send a message → runs graph → returns new assistant messages, state, trace |
| GET | `/providers/{id}` | provider details |
| GET | `/providers/{id}/slots?days=14` | open slots grouped by day |
| GET | `/appointments` | patient's appointments |
| POST | `/appointments` | `{provider_id, start_time, conversation_id}` → book (409 if taken) |
| POST | `/appointments/{id}/cancel` | cancel |
| GET | `/doctor/appointments` | doctor's upcoming appointments with AI summaries |
| GET | `/health` | health check (Fly) |
| GET | `/meta` | `{demo_mode, specialties}` |

---

## 6. Frontend (React + Vite + TypeScript)

* **Stack:** React 18, React Router, Tailwind CSS v4, Framer Motion, lucide-react icons. No heavy UI kit; custom glassmorphism components.
* **Brand:** "Your Health Guide". Palette: emerald/teal greens (`#059669`, `#10b981`, `#d1fae5`) on soft mint/white; logo = rounded green **medical plus** inside a soft glow.
* **Pages**
  * `/` Landing – sticky glass navbar with plus logo; hero with headline, CTA and a collage of doctor/nurse photos with floating stat chips; "How it works" (3 agents); specialties grid; why-us features; testimonials; CTA band; footer with medical disclaimer.
  * `/login`, `/register` – split screen with photo + form; patient/doctor tab on login.
  * `/app` – patient workspace: sidebar (new consultation, conversation history, appointments, health profile); chat panel with message bubbles, typing indicator, live **agent activity timeline** (Intake → Classifier → Matcher), specialty/urgency badge, provider recommendation cards (photo, rating, experience, match %, reason) → **slot picker** drawer (days × times) → confirmation dialog → success animation.
  * `/app/appointments` – upcoming/past with cancel.
  * `/app/profile` – editable medical history (chips for conditions, meds, allergies…).
  * `/doctor` – doctor dashboard: today/upcoming appointments, patient AI pre-visit summary.
* Responsive down to 360 px; accessible contrast; reduced-motion respected.
* Photos are bundled under `frontend/public/images` (Unsplash license) so the site has no hot-link dependency.

---

## 7. Configuration

| Env var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | – | enables GPT; absent ⇒ demo mode |
| `OPENAI_MODEL` | `gpt-4.1-mini` | chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | embeddings |
| `DATABASE_URL` | `sqlite:///./data/app.db` (Fly: `sqlite:////data/app.db`) | app DB (Postgres supported) |
| `CHECKPOINT_DB` | `./data/checkpoints.db` (Fly: `/data/checkpoints.db`) | LangGraph SQLite checkpointer; if `DATABASE_URL` is Postgres it's used instead |
| `JWT_SECRET` | dev value | **must** be set in prod |
| `MAX_FOLLOWUPS` | 4 | intake follow-up cap |
| `CORS_ORIGINS` | `http://localhost:5173` | dev only |

---

## 8. Deployment (Fly.io)

* Multi-stage `Dockerfile`: `node:20-alpine` builds `frontend/dist` → `python:3.12-slim` installs backend, copies dist to `/app/static`, runs `uvicorn app.main:app --host 0.0.0.0 --port 8080`.
* `fly.toml`: `internal_port = 8080`, `[[mounts]] source="yhg_data" destination="/data"`, HTTP health check on `/api/health`, `auto_stop_machines = "stop"`, `min_machines_running = 0`.
* Steps: `fly launch --no-deploy` → `fly volumes create yhg_data --size 1` → `fly secrets set OPENAI_API_KEY=… JWT_SECRET=…` → `fly deploy`.
* SQLite ⇒ run **one** machine. To scale horizontally, attach Fly Postgres and set `DATABASE_URL`.

---

## 9. Testing

* `backend/tests` (pytest, demo mode — no network): auth, graph intake loop (asks follow-ups then recommends), emergency red-flag path, slot generation & double-booking prevention, conversation persistence across graph invocations.
* Frontend: `npm run build` type-check.

---

## 10. Build plan (order of implementation)

1. Backend skeleton: config, DB, models, auth, seed.
2. Scheduling service (slots, booking).
3. Agents: specialties, prompts, LLM factory + fallbacks, nodes, graph + checkpointer.
4. Routers & static serving.
5. Tests.
6. Frontend: design system, landing, auth, patient workspace (chat, cards, slots), appointments, profile, doctor dashboard.
7. Dockerfile, fly.toml, README.
