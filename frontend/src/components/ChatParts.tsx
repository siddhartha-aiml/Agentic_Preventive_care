import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { Bot, CalendarCheck, CalendarClock, Check, ClipboardList, Database, Languages, MapPin, Siren, Star, Users, Volume2 } from "lucide-react";
import clsx from "clsx";
import { fmtDate, fmtTime, type ChatMessage, type Classification, type Recommendation } from "../lib/api";
import Avatar from "./Avatar";
import { specialtyIcon, UrgencyBadge } from "./specialty";
import { PlusMark } from "./Logo";

export const AGENT_STEPS: Record<string, { label: string; icon: typeof Bot }> = {
  load_context: { label: "Reviewing your health history", icon: Database },
  intake_agent: { label: "Symptom Intake Agent", icon: Bot },
  emergency: { label: "Safety check", icon: Siren },
  classify_specialty: { label: "Specialty Classifier", icon: ClipboardList },
  match_providers: { label: "Provider Matcher", icon: Users },
  summarize_memory: { label: "Saving to your health memory", icon: Database },
  concierge: { label: "Care Concierge", icon: Bot },
};

function Bubble({ children, mine }: { children: React.ReactNode; mine?: boolean }) {
  return (
    <div className={clsx("prose-chat max-w-[85%] rounded-3xl px-5 py-3.5 text-[15px] leading-relaxed sm:max-w-[75%]",
      mine ? "rounded-br-lg bg-gradient-to-br from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-600/20 [&_strong]:text-white"
           : "rounded-bl-lg bg-white text-slate-700 shadow-sm ring-1 ring-emerald-900/5")}>
      {children}
    </div>
  );
}

function BotAvatar() {
  return <PlusMark className="mt-1 h-8 w-8 shrink-0" glow={false} />;
}

function ClassificationCard({ c }: { c: Classification }) {
  const Icon = specialtyIcon(c.specialty);
  return (
    <div className="w-full max-w-xl overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-emerald-900/5">
      <div className="flex items-center gap-4 bg-gradient-to-r from-brand-600 to-teal-600 px-5 py-4 text-white">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20"><Icon className="h-6 w-6" /></span>
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-brand-100">Recommended specialty</p>
          <p className="text-xl font-bold">{c.specialty}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold">{Math.round(c.confidence * 100)}%</p>
          <p className="text-[11px] text-brand-100">confidence</p>
        </div>
      </div>
      <div className="space-y-3 px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <UrgencyBadge urgency={c.urgency} />
          {c.secondary_specialty && c.secondary_specialty !== c.specialty && (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">Also relevant: {c.secondary_specialty}</span>
          )}
        </div>
        <p className="text-sm leading-relaxed text-slate-600">{c.reasoning}</p>
      </div>
    </div>
  );
}

export function ProviderCard({ r, onSelect, index }: { r: Recommendation; onSelect: () => void; index: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08 }}
      className="group relative flex flex-col rounded-3xl bg-white p-5 shadow-sm ring-1 ring-emerald-900/5 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-900/10 hover:ring-brand-500/30">
      {index === 0 && <span className="absolute -top-2.5 left-5 rounded-full bg-gradient-to-r from-amber-400 to-orange-400 px-2.5 py-0.5 text-[11px] font-bold text-white shadow">Best match</span>}
      <div className="flex items-start gap-4">
        <Avatar name={r.name} src={r.photo_url} className="h-16 w-16 text-lg" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-bold text-slate-900">{r.name}</p>
          <p className="truncate text-xs text-slate-500">{r.title}</p>
          <div className="mt-1.5 flex items-center gap-1 text-xs text-slate-600">
            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" /> <b>{r.rating}</b> <span className="text-slate-400">({r.reviews_count})</span>
            <span className="mx-1 text-slate-300">•</span>{r.years_experience} yrs
          </div>
        </div>
        <div className="relative flex h-14 w-14 shrink-0 items-center justify-center">
          <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#d1fae5" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#059669" strokeWidth="3" strokeLinecap="round" strokeDasharray={`${(r.match_score / 100) * 97.4} 97.4`} />
          </svg>
          <span className="text-sm font-bold text-brand-700">{r.match_score}%</span>
        </div>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-slate-600">{r.reason}</p>
      {r.similar_cases.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {r.similar_cases.map((c) => <span key={c} className="rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-medium text-brand-700">Treated: {c}</span>)}
        </div>
      )}
      <div className="mt-4 space-y-1.5 text-xs text-slate-500">
        <p className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" />{r.location}</p>
        <p className="flex items-center gap-1.5"><Languages className="h-3.5 w-3.5" />{r.languages.join(", ")}</p>
        {r.next_available && <p className="flex items-center gap-1.5 font-semibold text-brand-700"><CalendarClock className="h-3.5 w-3.5" />Next: {fmtDate(r.next_available)} · {fmtTime(r.next_available)}</p>}
      </div>
      <button onClick={onSelect} className="btn-primary mt-5 w-full !py-2.5 text-sm"><CalendarCheck className="h-4 w-4" /> View slots & book</button>
    </motion.div>
  );
}

function ListenButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label="Listen to this message"
      className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 ring-1 ring-brand-600/20 transition hover:bg-brand-50">
      <Volume2 className="h-4 w-4" /> सुनें · Listen
    </button>
  );
}

export function MessageItem({ m, onSelectProvider, onSpeak }: { m: ChatMessage; onSelectProvider: (id: number) => void; onSpeak?: (m: ChatMessage) => void }) {
  const type = m.payload?.type;

  if (m.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <Bubble mine>{m.content}</Bubble>
      </motion.div>
    );
  }

  if (type === "booking") {
    const p = m.payload!;
    return (
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="flex justify-center">
        <div className="flex items-center gap-4 rounded-3xl bg-brand-50 px-5 py-4 ring-1 ring-brand-600/20">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white"><Check className="h-6 w-6" /></span>
          <div>
            <p className="font-bold text-brand-900">Appointment confirmed</p>
            <p className="text-sm text-brand-800">{p.provider_name} · {fmtDate(p.start_time, { weekday: "long", month: "short", day: "numeric" })} at {fmtTime(p.start_time)}</p>
          </div>
        </div>
      </motion.div>
    );
  }

  if (type === "emergency") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
        <BotAvatar />
        <div className="max-w-[85%] rounded-3xl rounded-bl-lg border border-red-200 bg-red-50 px-5 py-4 text-[15px] leading-relaxed text-red-900 shadow-sm sm:max-w-[75%]">
          <div className="mb-2 flex items-center gap-2 font-bold text-red-700"><Siren className="h-5 w-5" /> Urgent safety notice</div>
          <div className="prose-chat [&_strong]:text-red-800"><ReactMarkdown>{m.content}</ReactMarkdown></div>
          <div className="mt-3 flex flex-wrap gap-2">
            <a href="tel:112" className="inline-flex items-center gap-2 rounded-full bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700">Call 112 now</a>
            <a href="tel:108" className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-red-700 ring-1 ring-red-300 hover:bg-red-100">Ambulance 108</a>
            <a href="tel:14416" className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-bold text-red-700 ring-1 ring-red-300 hover:bg-red-100">Tele-MANAS 14416</a>
            {onSpeak && <ListenButton onClick={() => onSpeak(m)} />}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <BotAvatar />
      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex">
          <Bubble>
            {type === "followup" && (
              <span className="mb-1.5 inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700">
                Follow-up question {m.payload!.index}
              </span>
            )}
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </Bubble>
        </div>
        {onSpeak && <ListenButton onClick={() => onSpeak(m)} />}
        {type === "classification" && <ClassificationCard c={m.payload as unknown as Classification} />}
        {type === "recommendations" && (
          <div className="grid gap-4 pt-2 md:grid-cols-2">
            {(m.payload!.providers as Recommendation[]).map((r, i) => (
              <ProviderCard key={r.provider_id} r={r} index={i} onSelect={() => onSelectProvider(r.provider_id)} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

/** Shown while the graph runs: animates through the likely agent steps. */
export function ThinkingIndicator({ phase }: { phase: string }) {
  const steps = phase === "recommended" ? ["load_context", "concierge"] : ["load_context", "intake_agent", "classify_specialty", "match_providers"];
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, steps.length - 1)), 1400);
    return () => clearInterval(t);
  }, [steps.length]);
  const step = AGENT_STEPS[steps[i]];
  const Icon = step.icon;
  return (
    <div className="flex gap-3">
      <BotAvatar />
      <div className="flex items-center gap-3 rounded-3xl rounded-bl-lg bg-white px-5 py-3.5 shadow-sm ring-1 ring-emerald-900/5">
        <span className="flex gap-1">
          {[0, 1, 2].map((d) => (
            <motion.span key={d} className="h-2 w-2 rounded-full bg-brand-500" animate={{ y: [0, -5, 0], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 0.9, delay: d * 0.15 }} />
          ))}
        </span>
        <motion.span key={step.label} initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-1.5 text-sm font-medium text-slate-500">
          <Icon className="h-4 w-4 text-brand-600" /> {step.label}…
        </motion.span>
      </div>
    </div>
  );
}

export function TraceChips({ trace }: { trace: string[] }) {
  if (!trace.length) return null;
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-wrap items-center gap-1.5 pl-11 text-[11px] text-slate-400">
      <span className="font-semibold uppercase tracking-wider">Agents:</span>
      {trace.map((t, i) => {
        const s = AGENT_STEPS[t];
        if (!s) return null;
        return (
          <span key={i} className="inline-flex items-center gap-1">
            <span className="rounded-full bg-white px-2 py-0.5 font-medium text-slate-500 ring-1 ring-slate-200">{s.label}</span>
            {i < trace.length - 1 && <span>→</span>}
          </span>
        );
      })}
    </motion.div>
  );
}
