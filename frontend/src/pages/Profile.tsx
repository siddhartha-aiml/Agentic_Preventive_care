import { useEffect, useState, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, HeartPulse, LoaderCircle, Pill, Plus, Save, ShieldAlert, Users, X, Scissors } from "lucide-react";
import { api, type PatientProfile } from "../lib/api";

type ListKey = "conditions" | "medications" | "allergies" | "surgeries" | "family_history";

const SECTIONS: { key: ListKey; label: string; icon: typeof Pill; placeholder: string; color: string }[] = [
  { key: "conditions", label: "Medical conditions", icon: HeartPulse, placeholder: "e.g. Hypertension (since 2018)", color: "bg-rose-50 text-rose-600" },
  { key: "medications", label: "Current medications", icon: Pill, placeholder: "e.g. Metformin 500 mg twice daily", color: "bg-sky-50 text-sky-600" },
  { key: "allergies", label: "Allergies", icon: ShieldAlert, placeholder: "e.g. Penicillin", color: "bg-amber-50 text-amber-600" },
  { key: "surgeries", label: "Past surgeries", icon: Scissors, placeholder: "e.g. Appendectomy (2004)", color: "bg-violet-50 text-violet-600" },
  { key: "family_history", label: "Family history", icon: Users, placeholder: "e.g. Father: heart attack at 60", color: "bg-teal-50 text-teal-600" },
];

function ChipList({ items, onChange, placeholder }: { items: string[]; onChange: (v: string[]) => void; placeholder: string }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const v = draft.trim();
    if (v && !items.includes(v)) onChange([...items, v]);
    setDraft("");
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  };
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {items.map((it) => (
          <span key={it} className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 py-1.5 pl-3 pr-1.5 text-sm font-medium text-brand-800 ring-1 ring-brand-600/15">
            {it}
            <button onClick={() => onChange(items.filter((x) => x !== it))} className="rounded-full p-0.5 hover:bg-brand-200/60" aria-label={`Remove ${it}`}><X className="h-3.5 w-3.5" /></button>
          </span>
        ))}
        {items.length === 0 && <span className="text-sm text-slate-400">None added</span>}
      </div>
      <div className="mt-3 flex gap-2">
        <input className="input !py-2.5 text-sm" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={onKey} placeholder={placeholder} />
        <button onClick={add} className="btn-ghost !px-4 !py-2.5" aria-label="Add"><Plus className="h-4 w-4" /></button>
      </div>
    </div>
  );
}

export default function Profile() {
  const [params] = useSearchParams();
  const [p, setP] = useState<PatientProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.profile().then(setP); }, []);

  const save = async () => {
    if (!p) return;
    setBusy(true); setError("");
    try {
      setP(await api.saveProfile(p));
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (!p) return <div className="flex flex-1 items-center justify-center"><LoaderCircle className="h-8 w-8 animate-spin text-brand-500" /></div>;
  const set = <K extends keyof PatientProfile>(k: K, v: PatientProfile[K]) => setP({ ...p, [k]: v });

  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        {params.get("welcome") && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-6 rounded-3xl bg-gradient-to-r from-brand-600 to-teal-600 p-6 text-white">
            <p className="text-lg font-bold">Welcome to Your Health Guide! 🎉</p>
            <p className="mt-1 text-brand-50/90">Add your medical history below — the health agent uses it to ask better questions and recommend the right care.</p>
          </motion.div>
        )}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl font-semibold tracking-tight text-brand-950">Health profile</h1>
            <p className="mt-1 text-slate-600">Shared with the AI agent and the doctors you book with.</p>
          </div>
          <button onClick={save} disabled={busy} className="btn-primary !py-2.5">
            {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : saved ? <><Check className="h-4 w-4" /> Saved</> : <><Save className="h-4 w-4" /> Save changes</>}
          </button>
        </div>
        {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

        <div className="card mt-8 grid gap-4 p-6 sm:grid-cols-2">
          <div>
            <label className="label">Full name</label>
            <input className="input" value={p.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} />
          </div>
          <div>
            <label className="label">Phone</label>
            <input className="input" value={p.phone ?? ""} onChange={(e) => set("phone", e.target.value || null)} placeholder="+1 555 …" />
          </div>
          <div>
            <label className="label">Date of birth</label>
            <input type="date" className="input" value={p.date_of_birth ?? ""} onChange={(e) => set("date_of_birth", e.target.value || null)} />
          </div>
          <div>
            <label className="label">Sex</label>
            <select className="input" value={p.sex ?? ""} onChange={(e) => set("sex", e.target.value || null)}>
              <option value="">Prefer not to say</option>
              <option>Female</option>
              <option>Male</option>
              <option>Other</option>
            </select>
          </div>
        </div>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          {SECTIONS.map((s) => (
            <div key={s.key} className="card p-6">
              <div className="mb-4 flex items-center gap-3">
                <span className={`flex h-10 w-10 items-center justify-center rounded-2xl ${s.color}`}><s.icon className="h-5 w-5" /></span>
                <h2 className="font-bold text-slate-900">{s.label}</h2>
              </div>
              <ChipList items={p[s.key]} onChange={(v) => set(s.key, v)} placeholder={s.placeholder} />
            </div>
          ))}
          <div className="card p-6">
            <h2 className="mb-4 font-bold text-slate-900">Lifestyle & notes</h2>
            <textarea className="input min-h-[120px] text-sm" value={p.notes ?? ""} onChange={(e) => set("notes", e.target.value || null)} placeholder="Smoking, exercise, diet, anything else…" />
          </div>
        </div>
      </div>
    </div>
  );
}
