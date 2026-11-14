import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarCheck, CircleCheck, Clock, LoaderCircle, MapPin, Star, X } from "lucide-react";
import clsx from "clsx";
import { api, fmtDate, fmtTime, parseLocal, type Appointment, type DaySlots, type Provider } from "../lib/api";
import Avatar from "./Avatar";

interface Props {
  providerId: number | null;
  conversationId?: string;
  onClose: () => void;
  onBooked: (a: Appointment) => void;
}

export default function SlotPicker({ providerId, conversationId, onClose, onBooked }: Props) {
  const [provider, setProvider] = useState<Provider | null>(null);
  const [days, setDays] = useState<DaySlots[] | null>(null);
  const [dayIdx, setDayIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [booked, setBooked] = useState<Appointment | null>(null);

  useEffect(() => {
    if (!providerId) return;
    setProvider(null); setDays(null); setDayIdx(0); setSelected(null); setError(""); setBooked(null);
    Promise.all([api.provider(providerId), api.slots(providerId)])
      .then(([p, s]) => { setProvider(p); setDays(s); })
      .catch((e) => setError(e.message));
  }, [providerId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const day = days?.[dayIdx];
  const groups = useMemo(() => {
    const g: Record<string, { start: string; end: string }[]> = { Morning: [], Afternoon: [], Evening: [] };
    day?.slots.forEach((s) => {
      const h = parseLocal(s.start).getHours();
      g[h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening"].push(s);
    });
    return Object.entries(g).filter(([, v]) => v.length);
  }, [day]);

  const confirm = async () => {
    if (!providerId || !selected) return;
    setBusy(true); setError("");
    try {
      const a = await api.book(providerId, selected, conversationId);
      setBooked(a);
      onBooked(a);
    } catch (e: any) {
      setError(e.message);
      if (e.status === 409) api.slots(providerId).then(setDays);
      setSelected(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AnimatePresence>
      {providerId && (
        <motion.div className="fixed inset-0 z-[60] flex items-end justify-center bg-brand-950/40 backdrop-blur-sm sm:items-center sm:p-4"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.div role="dialog" aria-modal="true" aria-label="Choose an appointment time"
            className="relative flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-[2rem] bg-white shadow-2xl sm:rounded-[2rem]"
            initial={{ y: 60, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 60, opacity: 0 }} transition={{ type: "spring", damping: 26, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}>
            <button onClick={onClose} className="absolute right-4 top-4 z-10 rounded-full bg-white/80 p-2 text-slate-500 hover:bg-slate-100" aria-label="Close"><X className="h-5 w-5" /></button>

            {booked ? (
              <div className="flex flex-col items-center px-8 py-14 text-center">
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", damping: 12 }}
                  className="relative flex h-24 w-24 items-center justify-center rounded-full bg-brand-100">
                  <span className="absolute inset-0 animate-pulse-ring rounded-full bg-brand-400/40" />
                  <CircleCheck className="h-14 w-14 text-brand-600" />
                </motion.div>
                <h3 className="mt-6 font-display text-3xl font-semibold text-brand-950">You're booked!</h3>
                <p className="mt-2 text-slate-600">
                  {booked.provider.name} · {fmtDate(booked.start_time, { weekday: "long", month: "long", day: "numeric" })} at {fmtTime(booked.start_time)}
                </p>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500"><MapPin className="h-4 w-4" /> {booked.provider.location}</p>
                <p className="mt-6 max-w-sm rounded-2xl bg-brand-50 px-4 py-3 text-sm text-brand-800">Your doctor will receive an AI pre-visit summary of this conversation so you won't have to repeat yourself.</p>
                <button onClick={onClose} className="btn-primary mt-8">Done</button>
              </div>
            ) : (
              <>
                <div className="bg-gradient-to-br from-brand-50 to-white px-6 pb-5 pt-6 sm:px-8">
                  {provider ? (
                    <div className="flex items-start gap-4 pr-8">
                      <Avatar name={provider.name} src={provider.photo_url} className="h-16 w-16 text-lg" />
                      <div className="min-w-0">
                        <h3 className="text-xl font-bold text-slate-900">{provider.name}</h3>
                        <p className="text-sm text-slate-600">{provider.title}</p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                          <span className="flex items-center gap-1"><Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />{provider.rating} ({provider.reviews_count})</span>
                          <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{provider.location}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-16 animate-pulse rounded-2xl bg-brand-100/60" />
                  )}
                  {provider?.bio && <p className="mt-4 line-clamp-2 text-sm text-slate-600">{provider.bio}</p>}
                </div>

                <div className="scrollbar-thin flex-1 overflow-y-auto px-6 py-5 sm:px-8">
                  {!days && !error && <div className="flex justify-center py-16"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>}
                  {days && days.length === 0 && <p className="py-12 text-center text-slate-500">No open slots in the next two weeks.</p>}
                  {days && days.length > 0 && (
                    <>
                      <p className="text-sm font-semibold text-slate-700">Select a day</p>
                      <div className="scrollbar-thin -mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-2">
                        {days.map((d, i) => {
                          const dt = parseLocal(d.date + "T00:00:00");
                          return (
                            <button key={d.date} onClick={() => { setDayIdx(i); setSelected(null); }}
                              className={clsx("flex min-w-[68px] flex-col items-center rounded-2xl border px-3 py-2.5 transition",
                                i === dayIdx ? "border-brand-600 bg-brand-600 text-white shadow-lg shadow-brand-600/30" : "border-slate-200 bg-white hover:border-brand-400")}>
                              <span className={clsx("text-[11px] font-semibold uppercase", i === dayIdx ? "text-brand-100" : "text-slate-400")}>{dt.toLocaleDateString(undefined, { weekday: "short" })}</span>
                              <span className="text-xl font-bold">{dt.getDate()}</span>
                              <span className={clsx("text-[11px]", i === dayIdx ? "text-brand-100" : "text-slate-500")}>{d.slots.length} open</span>
                            </button>
                          );
                        })}
                      </div>
                      <div className="mt-4 space-y-4">
                        {groups.map(([label, slots]) => (
                          <div key={label}>
                            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400"><Clock className="h-3.5 w-3.5" />{label}</p>
                            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                              {slots.map((s) => (
                                <button key={s.start} onClick={() => setSelected(s.start)}
                                  className={clsx("rounded-xl border py-2.5 text-sm font-semibold transition",
                                    selected === s.start ? "border-brand-600 bg-brand-50 text-brand-800 ring-2 ring-brand-500/30" : "border-slate-200 text-slate-700 hover:border-brand-400 hover:bg-brand-50/50")}>
                                  {fmtTime(s.start)}
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>}
                </div>

                <div className="flex items-center justify-between gap-4 border-t border-slate-100 bg-white px-6 py-4 sm:px-8">
                  <p className="text-sm text-slate-600">
                    {selected ? <><span className="font-semibold text-slate-900">{fmtDate(selected)}</span> at <span className="font-semibold text-slate-900">{fmtTime(selected)}</span></> : "Pick a time that works for you"}
                  </p>
                  <button className="btn-primary" disabled={!selected || busy} onClick={confirm}>
                    {busy ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <><CalendarCheck className="h-4 w-4" /> Confirm booking</>}
                  </button>
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
