import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CalendarCheck, CalendarX, Clock, LoaderCircle, MapPin, MessageSquare, Plus } from "lucide-react";
import clsx from "clsx";
import { api, fmtDate, fmtTime, parseLocal, type Appointment } from "../lib/api";
import Avatar from "../components/Avatar";
import { specialtyIcon } from "../components/specialty";

export default function Appointments() {
  const [items, setItems] = useState<Appointment[] | null>(null);
  const [tab, setTab] = useState<"upcoming" | "past">("upcoming");

  const load = () => api.appointments().then(setItems);
  useEffect(() => { load(); }, []);

  const cancel = async (id: number) => {
    if (!confirm("Cancel this appointment?")) return;
    await api.cancel(id);
    load();
  };

  const now = new Date();
  const upcoming = (items ?? []).filter((a) => a.status === "booked" && parseLocal(a.end_time) >= now).sort((a, b) => a.start_time.localeCompare(b.start_time));
  const past = (items ?? []).filter((a) => !upcoming.includes(a));
  const list = tab === "upcoming" ? upcoming : past;

  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl font-semibold tracking-tight text-brand-950">Appointments</h1>
            <p className="mt-1 text-slate-600">Your upcoming visits and history.</p>
          </div>
          <Link to="/app" className="btn-primary !py-2.5"><Plus className="h-4 w-4" /> New consultation</Link>
        </div>

        <div className="mt-8 inline-flex rounded-2xl bg-white p-1 shadow-sm ring-1 ring-emerald-900/5">
          {(["upcoming", "past"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={clsx("rounded-xl px-5 py-2 text-sm font-semibold capitalize transition", tab === t ? "bg-brand-600 text-white shadow" : "text-slate-500 hover:text-brand-700")}>
              {t} {t === "upcoming" && upcoming.length > 0 && <span className="ml-1 opacity-80">({upcoming.length})</span>}
            </button>
          ))}
        </div>

        {!items && <div className="flex justify-center py-20"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>}
        {items && list.length === 0 && (
          <div className="card mt-6 flex flex-col items-center px-6 py-16 text-center">
            <span className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand-50 text-brand-600"><CalendarCheck className="h-8 w-8" /></span>
            <p className="mt-4 font-semibold text-slate-800">{tab === "upcoming" ? "No upcoming appointments" : "No past appointments"}</p>
            <p className="mt-1 text-sm text-slate-500">Start a consultation and our agents will match you with the right doctor.</p>
          </div>
        )}

        <div className="mt-6 space-y-4">
          {list.map((a, i) => {
            const Icon = specialtyIcon(a.provider.specialty);
            const start = parseLocal(a.start_time);
            return (
              <motion.div key={a.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                className={clsx("card flex flex-col gap-5 p-5 sm:flex-row sm:items-center", a.status === "cancelled" && "opacity-60")}>
                <div className="flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-teal-600 text-white">
                  <span className="text-xs font-semibold uppercase">{start.toLocaleDateString(undefined, { month: "short" })}</span>
                  <span className="text-3xl font-bold leading-none">{start.getDate()}</span>
                  <span className="text-[11px]">{start.toLocaleDateString(undefined, { weekday: "short" })}</span>
                </div>
                <div className="flex min-w-0 flex-1 items-center gap-4">
                  <Avatar name={a.provider.name} src={a.provider.photo_url} className="h-14 w-14" />
                  <div className="min-w-0">
                    <p className="font-bold text-slate-900">{a.provider.name}</p>
                    <p className="flex items-center gap-1.5 text-sm text-slate-600"><Icon className="h-4 w-4 text-brand-600" />{a.provider.specialty}</p>
                    <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{fmtTime(a.start_time)} – {fmtTime(a.end_time)}</span>
                      <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{a.provider.location}</span>
                    </div>
                    {a.reason && <p className="mt-1 truncate text-xs text-slate-400">Reason: {a.reason}</p>}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {a.status === "cancelled" && <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">Cancelled</span>}
                  {a.conversation_id && (
                    <Link to={`/app/c/${a.conversation_id}`} className="rounded-xl p-2.5 text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50" title="Open conversation">
                      <MessageSquare className="h-4 w-4" />
                    </Link>
                  )}
                  {tab === "upcoming" && (
                    <button onClick={() => cancel(a.id)} className="flex items-center gap-1.5 rounded-xl px-3 py-2.5 text-sm font-semibold text-red-600 ring-1 ring-red-200 hover:bg-red-50">
                      <CalendarX className="h-4 w-4" /> Cancel
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
        <p className="mt-6 text-center text-xs text-slate-400">Times shown in clinic local time · {fmtDate(new Date().toISOString().slice(0, 19), { year: "numeric", month: "long", day: "numeric" })}</p>
      </div>
    </div>
  );
}
