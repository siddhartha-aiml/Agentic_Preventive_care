import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Bot, CalendarCheck, Clock, LoaderCircle, LogOut, Pill, ShieldAlert, Siren, Star, UserRound, Users } from "lucide-react";
import clsx from "clsx";
import Logo from "../components/Logo";
import Avatar from "../components/Avatar";
import { UrgencyBadge } from "../components/specialty";
import { api, fmtDate, fmtTime, parseLocal, type DoctorAppointment, type Provider } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function Doctor() {
  const { logout } = useAuth();
  const nav = useNavigate();
  const [me, setMe] = useState<Provider | null>(null);
  const [appts, setAppts] = useState<DoctorAppointment[] | null>(null);
  const [sel, setSel] = useState<number | null>(null);

  useEffect(() => {
    api.doctorMe().then(setMe);
    api.doctorAppointments().then((a) => {
      setAppts(a);
      const first = a.find((x) => x.status === "booked" && parseLocal(x.end_time) >= new Date());
      setSel(first?.id ?? a[0]?.id ?? null);
    });
  }, []);

  const now = new Date();
  const upcoming = useMemo(() => (appts ?? []).filter((a) => a.status === "booked" && parseLocal(a.end_time) >= now), [appts]);
  const today = upcoming.filter((a) => parseLocal(a.start_time).toDateString() === now.toDateString());
  const urgent = upcoming.filter((a) => ["urgent", "emergency"].includes(a.ai_summary?.urgency));
  const current = (appts ?? []).find((a) => a.id === sel) ?? null;
  const s = current?.ai_summary ?? {};

  return (
    <div className="min-h-screen bg-mint">
      <header className="sticky top-0 z-30 border-b border-emerald-900/5 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <Logo to="/doctor" />
          <div className="flex items-center gap-3">
            {me && (
              <div className="hidden items-center gap-3 sm:flex">
                <Avatar name={me.name} src={me.photo_url} className="h-9 w-9 !rounded-full" />
                <div className="text-right">
                  <p className="text-sm font-semibold text-slate-800">{me.name}</p>
                  <p className="text-xs text-slate-400">{me.specialty}</p>
                </div>
              </div>
            )}
            <button onClick={() => { logout(); nav("/"); }} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Log out"><LogOut className="h-5 w-5" /></button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <h1 className="font-display text-4xl font-semibold tracking-tight text-brand-950">Good {now.getHours() < 12 ? "morning" : now.getHours() < 18 ? "afternoon" : "evening"}{me ? `, Dr. ${me.name.split(" ").slice(-1)[0]}` : ""}</h1>
        <p className="mt-1 text-slate-600">Your patients arrive pre-triaged — here's what they told our health agent.</p>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            { label: "Today", value: today.length, icon: CalendarCheck, cls: "from-brand-500 to-brand-700" },
            { label: "Upcoming (14 days)", value: upcoming.length, icon: Users, cls: "from-teal-500 to-cyan-700" },
            { label: "Flagged urgent", value: urgent.length, icon: Siren, cls: "from-orange-400 to-red-500" },
          ].map((k) => (
            <div key={k.label} className="card flex items-center gap-4 p-5">
              <span className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${k.cls} text-white`}><k.icon className="h-6 w-6" /></span>
              <div>
                <p className="text-3xl font-bold text-slate-900">{k.value}</p>
                <p className="text-sm text-slate-500">{k.label}</p>
              </div>
            </div>
          ))}
        </div>

        {!appts && <div className="flex justify-center py-20"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>}
        {appts && appts.length === 0 && (
          <div className="card mt-8 px-6 py-16 text-center">
            <CalendarCheck className="mx-auto h-10 w-10 text-brand-500" />
            <p className="mt-3 font-semibold text-slate-800">No appointments yet</p>
            <p className="text-sm text-slate-500">When patients book with you, their AI pre-visit summaries will appear here.</p>
          </div>
        )}
        {appts && appts.length > 0 && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[380px_1fr]">
            <div className="space-y-3">
              {appts.map((a) => (
                <button key={a.id} onClick={() => setSel(a.id)}
                  className={clsx("card flex w-full items-center gap-4 p-4 text-left transition", sel === a.id ? "ring-2 ring-brand-500" : "hover:ring-1 hover:ring-brand-300", a.status !== "booked" && "opacity-50")}>
                  <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl bg-brand-50 text-brand-800">
                    <span className="text-[10px] font-bold uppercase">{fmtDate(a.start_time, { month: "short" })}</span>
                    <span className="text-xl font-bold leading-none">{parseLocal(a.start_time).getDate()}</span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold text-slate-900">{a.patient_name}</p>
                    <p className="flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3.5 w-3.5" />{fmtTime(a.start_time)} · {a.status}</p>
                    <p className="mt-0.5 truncate text-xs text-slate-400">{a.reason ?? "General visit"}</p>
                  </div>
                  <UrgencyBadge urgency={a.ai_summary?.urgency} />
                </button>
              ))}
            </div>

            {current && (
              <motion.div key={current.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="card overflow-hidden">
                <div className="bg-gradient-to-r from-brand-600 to-teal-600 px-6 py-5 text-white">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/20"><UserRound className="h-6 w-6" /></span>
                      <div>
                        <p className="text-xl font-bold">{current.patient_name}</p>
                        <p className="text-sm text-brand-100">{[current.patient_age && `${current.patient_age} yrs`, current.patient_sex].filter(Boolean).join(" · ") || "—"}</p>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <p className="font-semibold">{fmtDate(current.start_time, { weekday: "long", month: "long", day: "numeric" })}</p>
                      <p className="text-brand-100">{fmtTime(current.start_time)} – {fmtTime(current.end_time)}</p>
                    </div>
                  </div>
                </div>
                <div className="space-y-6 p-6">
                  <section>
                    <div className="flex items-center gap-2">
                      <Bot className="h-5 w-5 text-brand-600" />
                      <h3 className="font-bold text-slate-900">AI pre-visit summary</h3>
                      {s.emergency && <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">Red flag raised</span>}
                    </div>
                    <p className="mt-3 rounded-2xl bg-brand-50/60 p-4 text-sm leading-relaxed text-slate-700">{s.symptom_summary || "Booked directly — no AI intake available."}</p>
                    {s.specialty && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                        <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-700">Triage: {s.specialty}</span>
                        <UrgencyBadge urgency={s.urgency} />
                      </div>
                    )}
                    {s.reasoning && <p className="mt-2 text-xs text-slate-500">{s.reasoning}</p>}
                  </section>

                  <section className="grid gap-4 sm:grid-cols-3">
                    {[
                      { label: "Conditions", items: current.patient_conditions, icon: Star },
                      { label: "Medications", items: current.patient_medications, icon: Pill },
                      { label: "Allergies", items: current.patient_allergies, icon: ShieldAlert },
                    ].map((g) => (
                      <div key={g.label} className="rounded-2xl ring-1 ring-slate-100 p-4">
                        <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-400"><g.icon className="h-3.5 w-3.5" />{g.label}</p>
                        <ul className="mt-2 space-y-1 text-sm text-slate-700">
                          {g.items.length ? g.items.map((i) => <li key={i}>• {i}</li>) : <li className="text-slate-400">None recorded</li>}
                        </ul>
                      </div>
                    ))}
                  </section>

                  {Array.isArray(s.transcript) && s.transcript.length > 0 && (
                    <section>
                      <h3 className="font-bold text-slate-900">Intake conversation</h3>
                      <div className="scrollbar-thin mt-3 max-h-80 space-y-2 overflow-y-auto rounded-2xl bg-slate-50 p-4">
                        {s.transcript.map((t: { role: string; content: string }, i: number) => (
                          <div key={i} className={clsx("text-sm", t.role === "user" ? "text-slate-800" : "text-slate-500")}>
                            <span className="font-semibold">{t.role === "user" ? "Patient" : "Agent"}:</span> {t.content.replace(/\*\*/g, "")}
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
                </div>
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
