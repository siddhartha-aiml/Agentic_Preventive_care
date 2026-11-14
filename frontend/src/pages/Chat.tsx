import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, CalendarCheck, ClipboardList, LoaderCircle, Send, ShieldCheck, Users } from "lucide-react";
import clsx from "clsx";
import { api, type ChatMessage, type ChatState } from "../lib/api";
import { MessageItem, ThinkingIndicator, TraceChips } from "../components/ChatParts";
import SlotPicker from "../components/SlotPicker";
import { specialtyIcon, UrgencyBadge } from "../components/specialty";
import { PlusMark } from "../components/Logo";
import { useAuth } from "../lib/auth";
import { useWorkspace } from "./Workspace";

const SUGGESTIONS = [
  "I've had a throbbing headache with nausea for 3 days",
  "My chest feels tight when I climb stairs",
  "I have an itchy red rash on my arms",
  "I've been feeling anxious and can't sleep",
  "Lower back pain after lifting something heavy",
  "Burning in my chest after meals",
];

function Composer({ onSend, busy, autoFocus }: { onSend: (t: string) => void; busy: boolean; autoFocus?: boolean }) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [text]);
  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };
  return (
    <form onSubmit={submit} className="glass flex items-end gap-2 rounded-[1.75rem] p-2 pl-5">
      <textarea ref={ref} rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} autoFocus={autoFocus}
        placeholder="Describe your symptoms or answer the question…" aria-label="Message"
        className="max-h-[180px] flex-1 resize-none bg-transparent py-3 text-[15px] text-slate-800 outline-none placeholder:text-slate-400" />
      <button type="submit" disabled={busy || !text.trim()} aria-label="Send"
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-lg shadow-brand-600/30 transition hover:scale-105 disabled:opacity-40 disabled:hover:scale-100">
        {busy ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
      </button>
    </form>
  );
}

function Progress({ state, booked }: { state: ChatState | null; booked: boolean }) {
  const steps = [
    { key: "intake", label: "Symptom intake", icon: Bot },
    { key: "classify", label: "Specialty", icon: ClipboardList },
    { key: "match", label: "Matched doctors", icon: Users },
    { key: "book", label: "Booked", icon: CalendarCheck },
  ];
  const active = booked ? 4 : state?.phase === "recommended" ? 3 : state && state.followup_count > 0 ? 1 : 0;
  const cls = state?.classification;
  const Icon = specialtyIcon(cls?.specialty);
  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-5 overflow-y-auto border-l border-emerald-900/5 bg-white/60 p-6 xl:flex">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.15em] text-slate-400">Your care journey</p>
        <ol className="mt-4 space-y-1">
          {steps.map((s, i) => {
            const done = i < active;
            const current = i === active;
            return (
              <li key={s.key} className="flex items-center gap-3 py-1.5">
                <span className={clsx("flex h-9 w-9 items-center justify-center rounded-xl transition",
                  done ? "bg-brand-600 text-white" : current ? "bg-brand-100 text-brand-700 ring-2 ring-brand-500/40" : "bg-slate-100 text-slate-400")}>
                  <s.icon className="h-4 w-4" />
                </span>
                <span className={clsx("text-sm font-semibold", done || current ? "text-slate-800" : "text-slate-400")}>{s.label}</span>
              </li>
            );
          })}
        </ol>
      </div>
      {state?.phase === "intake" && (
        <div className="rounded-3xl bg-brand-50/70 p-5 ring-1 ring-brand-600/10">
          <p className="text-sm font-semibold text-brand-900">Follow-up questions</p>
          <div className="mt-3 flex gap-1.5">
            {Array.from({ length: state.max_followups }).map((_, i) => (
              <span key={i} className={clsx("h-2 flex-1 rounded-full", i < state.followup_count ? "bg-brand-500" : "bg-brand-200/60")} />
            ))}
          </div>
          <p className="mt-2 text-xs text-brand-800/70">The agent asks only what it needs — usually 2–4 questions.</p>
        </div>
      )}
      {cls && (
        <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-emerald-900/5">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-100 text-brand-700"><Icon className="h-5 w-5" /></span>
            <div>
              <p className="text-xs text-slate-400">Specialty</p>
              <p className="font-bold text-slate-800">{cls.specialty}</p>
            </div>
          </div>
          <div className="mt-3"><UrgencyBadge urgency={cls.urgency} /></div>
          {state?.symptom_summary && <p className="mt-3 line-clamp-6 text-xs leading-relaxed text-slate-500">{state.symptom_summary}</p>}
        </div>
      )}
      <div className="mt-auto flex gap-3 rounded-3xl bg-slate-50 p-4 text-xs leading-relaxed text-slate-500">
        <ShieldCheck className="h-5 w-5 shrink-0 text-brand-600" />
        This assistant helps you find the right care and does not provide a diagnosis. In an emergency, call 112.
      </div>
    </aside>
  );
}

export default function Chat() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const { upsert, refresh } = useWorkspace();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<ChatState | null>(null);
  const [trace, setTrace] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [picker, setPicker] = useState<number | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const pendingFirst = useRef<string | null>(null);

  useEffect(() => {
    setTrace([]);
    setError("");
    if (!id) {
      setMessages([]);
      setState(null);
      return;
    }
    setLoading(true);
    api
      .conversation(id)
      .then((d) => {
        setMessages(d.messages);
        setState(d.state);
        if (pendingFirst.current) {
          const t = pendingFirst.current;
          pendingFirst.current = null;
          send(t, id);
        }
      })
      .catch(() => nav("/app"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const send = async (text: string, convId = id) => {
    if (!convId) {
      // Start a new conversation, then send.
      setBusy(true);
      try {
        const c = await api.createConversation();
        upsert(c);
        pendingFirst.current = text;
        nav(`/app/c/${c.id}`);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setBusy(false);
      }
      return;
    }
    setError("");
    setBusy(true);
    setTrace([]);
    const optimistic: ChatMessage = { id: -Date.now(), role: "user", content: text, payload: null, created_at: new Date().toISOString() };
    setMessages((m) => [...m, optimistic]);
    try {
      const r = await api.send(convId, text);
      setMessages((m) => [...m, ...r.messages]);
      setState(r.state);
      setTrace(r.trace);
      upsert(r.conversation);
    } catch (e: any) {
      setError(e.message);
      setMessages((m) => m.filter((x) => x.id !== optimistic.id));
    } finally {
      setBusy(false);
    }
  };

  const onBooked = async () => {
    if (!id) return;
    const d = await api.conversation(id);
    setMessages(d.messages);
    refresh();
  };

  const booked = messages.some((m) => m.payload?.type === "booking");
  const firstName = user?.full_name.split(" ")[0] ?? "";

  // Empty state (no conversation yet)
  if (!id) {
    return (
      <div className="relative flex flex-1 flex-col overflow-y-auto">
        <div className="absolute inset-x-0 top-0 h-80 bg-gradient-to-b from-brand-100/70 to-transparent" />
        <div className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-4 py-10 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center">
            <PlusMark className="mx-auto h-16 w-16" />
            <h1 className="mt-6 font-display text-4xl font-semibold tracking-tight text-brand-950 sm:text-5xl">How are you feeling today, {firstName}?</h1>
            <p className="mx-auto mt-3 max-w-lg text-slate-600">Describe your symptoms in your own words. I'll ask a few questions, find the right specialist and help you book.</p>
          </motion.div>
          <div className="mt-10"><Composer onSend={(t) => send(t)} busy={busy} autoFocus /></div>
          {error && <p className="mt-3 text-center text-sm text-red-600">{error}</p>}
          <div className="mt-6 grid gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map((s, i) => (
              <motion.button key={s} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}
                onClick={() => send(s)} disabled={busy}
                className="rounded-2xl border border-emerald-900/5 bg-white px-4 py-3 text-left text-sm text-slate-600 shadow-sm transition hover:border-brand-400 hover:text-brand-800 hover:shadow-md">
                {s}
              </motion.button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="scrollbar-thin flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-5 px-4 py-8 sm:px-6">
            {loading && <div className="flex justify-center py-20"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>}
            {messages.map((m) => <MessageItem key={m.id} m={m} onSelectProvider={setPicker} />)}
            {busy && <ThinkingIndicator phase={state?.phase ?? "intake"} />}
            {!busy && <TraceChips trace={trace} />}
            {error && <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <div ref={bottom} />
          </div>
        </div>
        <div className="mx-auto w-full max-w-3xl px-4 pb-5 sm:px-6">
          <Composer onSend={(t) => send(t)} busy={busy} />
          <p className="mt-2 text-center text-[11px] text-slate-400">Not a diagnosis. If this is an emergency, call 112 (ambulance 108).</p>
        </div>
      </div>
      <Progress state={state} booked={booked} />
      <SlotPicker providerId={picker} conversationId={id} onClose={() => setPicker(null)} onBooked={onBooked} />
    </div>
  );
}
