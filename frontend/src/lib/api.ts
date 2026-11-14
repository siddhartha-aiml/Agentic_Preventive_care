import type { VoiceConfig } from "./voice";

export type Role = "patient" | "doctor";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
}

export interface Recommendation {
  provider_id: number;
  name: string;
  specialty: string;
  title: string;
  rating: number;
  reviews_count: number;
  years_experience: number;
  photo_url: string | null;
  location: string;
  languages: string[];
  match_score: number;
  similar_cases: string[];
  next_available: string | null;
  reason: string;
}

export interface Classification {
  specialty: string;
  secondary_specialty: string;
  confidence: number;
  urgency: "routine" | "soon" | "urgent" | "emergency";
  reasoning: string;
  title: string;
}

export interface ChatState {
  phase: "intake" | "recommended";
  followup_count: number;
  max_followups: number;
  classification: Classification | null;
  recommendations: Recommendation[];
  emergency: { reason: string } | null;
  symptom_summary: string;
  language?: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  payload: Record<string, any> | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  phase: string;
  specialty: string | null;
  urgency: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
  state: ChatState;
}

export interface SendResult {
  messages: ChatMessage[];
  state: ChatState;
  trace: string[];
  conversation: Conversation;
}

export interface Provider {
  id: number;
  name: string;
  specialty: string;
  title: string;
  years_experience: number;
  rating: number;
  reviews_count: number;
  bio: string;
  location: string;
  languages: string[];
  photo_url: string | null;
  accepts_new: boolean;
}

export interface DaySlots {
  date: string;
  slots: { start: string; end: string }[];
}

export interface Appointment {
  id: number;
  provider: Provider;
  start_time: string;
  end_time: string;
  status: "booked" | "cancelled" | "completed";
  reason: string | null;
  conversation_id: string | null;
  ai_summary: Record<string, any> | null;
}

export interface DoctorAppointment {
  id: number;
  start_time: string;
  end_time: string;
  status: string;
  reason: string | null;
  ai_summary: Record<string, any> | null;
  patient_name: string;
  patient_age: number | null;
  patient_sex: string | null;
  patient_conditions: string[];
  patient_medications: string[];
  patient_allergies: string[];
}

export interface PatientProfile {
  full_name?: string | null;
  email?: string | null;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  conditions: string[];
  medications: string[];
  allergies: string[];
  surgeries: string[];
  family_history: string[];
  notes: string | null;
}

export interface Meta {
  app_name: string;
  demo_mode: boolean;
  agent_mode: "gpt" | "demo" | "degraded";
  llm_last_error_type: string | null;
  model: string | null;
  specialties: { name: string; description: string; icon: string }[];
  demo_accounts: {
    patient: { email: string; password: string };
    doctor_password: string;
    doctors: { name: string; specialty: string; email: string }[];
  } | null;
}

const TOKEN_KEY = "yhg_token";

export const tokenStore = {
  get: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (t: string | null) => {
    try {
      if (t) localStorage.setItem(TOKEN_KEY, t);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token) {
      tokenStore.set(null);
      window.dispatchEvent(new Event("yhg:logout"));
    }
    const detail = Array.isArray(data.detail) ? data.detail.map((d: any) => d.msg).join(", ") : data.detail;
    throw new ApiError(res.status, detail || "Something went wrong");
  }
  return data as T;
}

const body = (b: unknown) => JSON.stringify(b);

export const api = {
  meta: () => request<Meta>("/meta"),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", { method: "POST", body: body({ email, password }) }),
  register: (data: { email: string; password: string; full_name: string; date_of_birth?: string | null; sex?: string | null }) =>
    request<{ access_token: string; user: User }>("/auth/register", { method: "POST", body: body(data) }),
  me: () => request<User>("/auth/me"),

  conversations: () => request<Conversation[]>("/conversations"),
  createConversation: (language?: string) =>
    request<ConversationDetail>(`/conversations${language ? `?language=${encodeURIComponent(language)}` : ""}`, { method: "POST" }),
  conversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
  send: (id: string, content: string, language?: string) =>
    request<SendResult>(`/conversations/${id}/messages`, { method: "POST", body: body({ content, language }) }),

  voiceConfig: () => request<VoiceConfig>("/voice/config"),
  transcribe: (audio: Blob, language: string) => {
    const form = new FormData();
    form.append("file", audio, "speech.wav");
    form.append("language", language);
    return request<{ transcript: string; language_code: string }>("/voice/transcribe", { method: "POST", body: form });
  },
  speak: (text: string, language: string) =>
    request<{ mime: string; audio_base64: string }>("/voice/speak", { method: "POST", body: body({ text, language }) }),

  provider: (id: number) => request<Provider>(`/providers/${id}`),
  slots: (id: number) => request<DaySlots[]>(`/providers/${id}/slots?days=14`),

  appointments: () => request<Appointment[]>("/appointments"),
  book: (provider_id: number, start_time: string, conversation_id?: string) =>
    request<Appointment>("/appointments", { method: "POST", body: body({ provider_id, start_time, conversation_id }) }),
  cancel: (id: number) => request<Appointment>(`/appointments/${id}/cancel`, { method: "POST" }),

  profile: () => request<PatientProfile>("/patients/me"),
  saveProfile: (p: PatientProfile) => request<PatientProfile>("/patients/me", { method: "PUT", body: body(p) }),

  doctorMe: () => request<Provider>("/doctor/me"),
  doctorAppointments: () => request<DoctorAppointment[]>("/doctor/appointments"),
};

// Server datetimes are naive clinic-local times; parse them as local wall-clock times.
export const parseLocal = (iso: string) => new Date(iso.replace("Z", ""));
export const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", month: "short", day: "numeric" }) =>
  parseLocal(iso).toLocaleDateString(undefined, opts);
export const fmtTime = (iso: string) => parseLocal(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
