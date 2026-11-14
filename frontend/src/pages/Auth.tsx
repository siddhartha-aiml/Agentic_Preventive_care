import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, LoaderCircle, Stethoscope, UserRound } from "lucide-react";
import clsx from "clsx";
import Logo from "../components/Logo";
import { useAuth } from "../lib/auth";
import { api, type Meta } from "../lib/api";

function Shell({ children, image, quote }: { children: ReactNode; image: string; quote: string }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="flex flex-1 items-center justify-center py-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="w-full max-w-md">
            {children}
          </motion.div>
        </div>
      </div>
      <div className="relative hidden overflow-hidden lg:block">
        <img src={image} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-brand-950/90 via-brand-900/30 to-transparent" />
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <p className="font-display text-3xl font-semibold leading-snug">{quote}</p>
          <p className="mt-3 text-brand-200">Your Health Guide · AI-guided preventive care</p>
        </div>
      </div>
    </div>
  );
}

function ErrorBox({ error }: { error: string }) {
  if (!error) return null;
  return <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700 ring-1 ring-red-600/15">{error}</div>;
}

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [role, setRole] = useState<"patient" | "doctor">("patient");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<Meta["demo_accounts"]>(null);
  useEffect(() => { api.meta().then((m) => setDemo(m.demo_accounts)).catch(() => {}); }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = await login(email, password);
      nav(u.role === "doctor" ? "/doctor" : "/app");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const fillPatient = () => {
    if (!demo) return;
    setEmail(demo.patient.email);
    setPassword(demo.patient.password);
  };
  const fillDoctor = (docEmail: string) => {
    if (!demo || !docEmail) return;
    setEmail(docEmail);
    setPassword(demo.doctor_password);
  };

  return (
    <Shell image={role === "patient" ? "/images/doctor-woman.jpg" : "/images/doctor-scan.jpg"} quote={role === "patient" ? "“Care that starts with listening.”" : "“Walk into every visit already knowing the story.”"}>
      <h1 className="font-display text-4xl font-semibold tracking-tight text-brand-950">Welcome back</h1>
      <p className="mt-2 text-slate-600">Log in to continue to your health portal.</p>

      <div className="mt-8 grid grid-cols-2 gap-1 rounded-2xl bg-brand-50 p-1 ring-1 ring-brand-600/10">
        {([["patient", "Patient", UserRound], ["doctor", "Doctor", Stethoscope]] as const).map(([r, label, Icon]) => (
          <button key={r} type="button" onClick={() => { setRole(r); setError(""); }}
            className={clsx("flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition",
              role === r ? "bg-white text-brand-800 shadow-sm" : "text-slate-500 hover:text-brand-700")}>
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-6 space-y-4">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder={role === "patient" ? "you@example.com" : "firstname.lastname@yourhealthguide.dev"} />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input id="password" type="password" required autoComplete="current-password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full py-3.5" disabled={busy}>
          {busy ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <>Log in <ArrowRight className="h-4 w-4" /></>}
        </button>
      </form>
      {demo && role === "patient" && (
        <button type="button" onClick={fillPatient} className="mt-4 w-full rounded-2xl border border-dashed border-brand-600/30 py-2.5 text-sm font-medium text-brand-700 hover:bg-brand-50">
          Use demo patient (Alex Morgan)
        </button>
      )}
      {demo && role === "doctor" && (
        <select className="input mt-4 border-dashed text-sm" defaultValue="" onChange={(e) => fillDoctor(e.target.value)} aria-label="Demo doctor">
          <option value="" disabled>Pick a demo doctor account…</option>
          {demo.doctors.map((d) => (
            <option key={d.email} value={d.email}>{d.name} — {d.specialty}</option>
          ))}
        </select>
      )}
      {role === "patient" && (
        <p className="mt-6 text-center text-sm text-slate-600">
          New here? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link>
        </p>
      )}
    </Shell>
  );
}

export function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", date_of_birth: "", sex: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register({ ...form, date_of_birth: form.date_of_birth || null, sex: form.sex || null });
      nav("/app/profile?welcome=1");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell image="/images/nurse-teal.jpg" quote="“Preventive care is the kindest care.”">
      <h1 className="font-display text-4xl font-semibold tracking-tight text-brand-950">Create your account</h1>
      <p className="mt-2 text-slate-600">Two minutes to set up. Free forever for patients.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <div>
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" required className="input" value={form.full_name} onChange={set("full_name")} placeholder="Jane Doe" />
        </div>
        <div>
          <label className="label" htmlFor="remail">Email</label>
          <input id="remail" type="email" required className="input" value={form.email} onChange={set("email")} placeholder="you@example.com" />
        </div>
        <div>
          <label className="label" htmlFor="rpw">Password</label>
          <input id="rpw" type="password" required minLength={6} className="input" value={form.password} onChange={set("password")} placeholder="At least 6 characters" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="dob">Date of birth</label>
            <input id="dob" type="date" className="input" value={form.date_of_birth} onChange={set("date_of_birth")} />
          </div>
          <div>
            <label className="label" htmlFor="sex">Sex</label>
            <select id="sex" className="input" value={form.sex} onChange={set("sex")}>
              <option value="">Prefer not to say</option>
              <option>Female</option>
              <option>Male</option>
              <option>Other</option>
            </select>
          </div>
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full py-3.5" disabled={busy}>
          {busy ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <>Create account <ArrowRight className="h-4 w-4" /></>}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Already registered? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Log in</Link>
      </p>
    </Shell>
  );
}
