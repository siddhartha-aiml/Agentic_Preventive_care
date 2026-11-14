import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Bot,
  CalendarCheck,
  ClipboardList,
  HeartHandshake,
  History,
  Lock,
  Menu,
  Quote,
  ShieldCheck,
  Sparkles,
  Star,
  Stethoscope,
  Users,
  X,
} from "lucide-react";
import Logo, { PlusMark } from "../components/Logo";
import { specialtyIcon } from "../components/specialty";
import { useAuth } from "../lib/auth";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] as const } }),
};

const SPECIALTIES = [
  "General Physician", "Cardiology", "Neurology", "Dermatology", "Gastroenterology", "Pulmonology", "Orthopedics",
  "ENT", "Endocrinology", "Psychiatry", "Ophthalmology", "Urology", "Obstetrics & Gynecology",
];

function Navbar() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 12);
    on();
    window.addEventListener("scroll", on);
    return () => window.removeEventListener("scroll", on);
  }, []);
  const home = user ? (user.role === "doctor" ? "/doctor" : "/app") : null;
  const links = [
    ["How it works", "#how"],
    ["Specialties", "#specialties"],
    ["Our care team", "#team"],
    ["Stories", "#stories"],
  ];
  return (
    <header className={`fixed inset-x-0 top-0 z-50 transition-all ${scrolled ? "py-2" : "py-4"}`}>
      <nav className={`mx-auto flex max-w-7xl items-center justify-between rounded-full px-4 py-2.5 sm:px-6 ${scrolled ? "glass mx-3 sm:mx-auto" : ""}`}>
        <Logo />
        <div className="hidden items-center gap-8 md:flex">
          {links.map(([l, h]) => (
            <a key={h} href={h} className="text-sm font-medium text-slate-600 transition hover:text-brand-700">{l}</a>
          ))}
        </div>
        <div className="hidden items-center gap-3 md:flex">
          {home ? (
            <Link to={home} className="btn-primary !py-2.5">Open my portal <ArrowRight className="h-4 w-4" /></Link>
          ) : (
            <>
              <Link to="/login" className="text-sm font-semibold text-brand-800 hover:text-brand-600">Log in</Link>
              <Link to="/register" className="btn-primary !py-2.5">Get started <ArrowRight className="h-4 w-4" /></Link>
            </>
          )}
        </div>
        <button className="rounded-full p-2 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X /> : <Menu />}
        </button>
      </nav>
      {open && (
        <div className="glass mx-3 mt-2 flex flex-col gap-1 rounded-3xl p-4 md:hidden">
          {links.map(([l, h]) => (
            <a key={h} href={h} onClick={() => setOpen(false)} className="rounded-xl px-3 py-2 font-medium text-slate-700 hover:bg-brand-50">{l}</a>
          ))}
          <div className="mt-2 flex gap-2">
            {home ? (
              <Link to={home} className="btn-primary flex-1">Open portal</Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost flex-1">Log in</Link>
                <Link to="/register" className="btn-primary flex-1">Sign up</Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden pb-20 pt-32 sm:pt-40">
      <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_70%)]" />
      <div className="absolute -left-40 -top-40 h-[520px] w-[520px] rounded-full bg-brand-300/40 blur-3xl" />
      <div className="absolute -right-32 top-20 h-[460px] w-[460px] rounded-full bg-teal-200/50 blur-3xl" />
      {/* decorative plus symbols */}
      <div className="pointer-events-none absolute inset-0 hidden lg:block" aria-hidden>
        <PlusMark className="absolute right-[44%] top-[16%] h-8 w-8 animate-float opacity-60" glow={false} />
        <PlusMark className="absolute bottom-[12%] left-[46%] h-5 w-5 animate-float opacity-40 [animation-delay:1.5s]" glow={false} />
      </div>

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <motion.div variants={fadeUp} initial="hidden" animate="show" className="inline-flex items-center gap-2 rounded-full border border-brand-600/15 bg-white/80 px-3 py-1.5 text-sm font-semibold text-brand-700 shadow-sm">
            <Sparkles className="h-4 w-4" /> AI-guided preventive care
          </motion.div>
          <motion.h1 variants={fadeUp} custom={1} initial="hidden" animate="show" className="mt-6 font-display text-5xl font-semibold leading-[1.05] tracking-tight text-brand-950 sm:text-6xl lg:text-7xl">
            The right doctor,<br />
            <span className="text-gradient italic">right when you need it.</span>
          </motion.h1>
          <motion.p variants={fadeUp} custom={2} initial="hidden" animate="show" className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600">
            Tell our health agent how you feel. It asks the right follow-up questions, considers your medical history,
            identifies the specialty you need and matches you with doctors who've treated cases like yours — then books you in.
          </motion.p>
          <motion.div variants={fadeUp} custom={3} initial="hidden" animate="show" className="mt-9 flex flex-wrap items-center gap-3">
            <Link to="/register" className="btn-primary px-7 py-4 text-base">Check my symptoms <ArrowRight className="h-5 w-5" /></Link>
            <Link to="/login" className="btn-ghost px-7 py-4 text-base">I already have an account</Link>
          </motion.div>
          <motion.div variants={fadeUp} custom={4} initial="hidden" animate="show" className="mt-10 flex items-center gap-5">
            <div className="flex -space-x-3">
              {["doctor-woman", "doctor-man", "nurse-teal", "nurse-man"].map((n) => (
                <img key={n} src={`/images/${n}.jpg`} alt="" className="h-11 w-11 rounded-full border-2 border-white object-cover" />
              ))}
            </div>
            <div>
              <div className="flex items-center gap-1 text-amber-400">
                {Array.from({ length: 5 }).map((_, i) => <Star key={i} className="h-4 w-4 fill-current" />)}
                <span className="ml-1 text-sm font-bold text-slate-800">4.9</span>
              </div>
              <p className="text-sm text-slate-500">30+ specialists across 13 specialties</p>
            </div>
          </motion.div>
        </div>

        {/* Photo collage */}
        <div className="relative mx-auto h-[540px] w-full max-w-[560px]">
          <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }}
            className="absolute left-[8%] top-0 h-[400px] w-[62%] overflow-hidden rounded-[2.5rem] border-[6px] border-white shadow-2xl shadow-brand-900/20">
            <img src="/images/doctor-woman.jpg" alt="Smiling doctor in a white coat" className="h-full w-full object-cover" />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
            className="absolute bottom-0 right-0 h-[300px] w-[48%] overflow-hidden rounded-[2.5rem] border-[6px] border-white shadow-2xl shadow-brand-900/20">
            <img src="/images/nurse-teal.jpg" alt="Nurse in teal scrubs" className="h-full w-full object-cover" />
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.35 }}
            className="absolute bottom-6 left-0 h-[170px] w-[38%] overflow-hidden rounded-[2rem] border-[6px] border-white shadow-xl shadow-brand-900/20">
            <img src="/images/nurse-man.jpg" alt="Male nurse with stethoscope" className="h-full w-full object-cover" />
          </motion.div>

          {/* floating chips */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}
            className="glass absolute -left-2 top-16 flex animate-float items-center gap-3 rounded-2xl px-4 py-3 sm:-left-8">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700"><Bot className="h-5 w-5" /></span>
            <div>
              <p className="text-xs font-medium text-slate-500">Health agent</p>
              <p className="text-sm font-bold text-slate-800">“When did it start?”</p>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }}
            className="glass absolute right-0 top-[38%] flex animate-float items-center gap-3 rounded-2xl px-4 py-3 [animation-delay:2s] sm:-right-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-100 text-rose-600"><Stethoscope className="h-5 w-5" /></span>
            <div>
              <p className="text-xs font-medium text-slate-500">Matched specialty</p>
              <p className="text-sm font-bold text-slate-800">Cardiology · 94% fit</p>
            </div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }}
            className="glass absolute bottom-[42%] left-[30%] hidden items-center gap-3 rounded-2xl px-4 py-3 sm:flex">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-brand-500" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-brand-500" />
            </span>
            <p className="text-sm font-bold text-slate-800">Booked · Tue 10:30 AM</p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function Stats() {
  const stats = [
    ["< 3 min", "from symptoms to booked visit"],
    ["13", "medical specialties covered"],
    ["3", "AI agents working for you"],
    ["24/7", "always-on health guidance"],
  ];
  return (
    <section className="relative mx-auto -mt-4 max-w-6xl px-4 sm:px-6">
      <div className="card grid grid-cols-2 gap-6 p-8 md:grid-cols-4">
        {stats.map(([n, l], i) => (
          <motion.div key={l} variants={fadeUp} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }} className="text-center">
            <p className="font-display text-4xl font-semibold text-brand-700">{n}</p>
            <p className="mt-1 text-sm text-slate-500">{l}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    { icon: Bot, title: "Symptom Intake Agent", text: "Describe how you feel in your own words. The agent asks a few smart follow-up questions — onset, severity, triggers — and reads your health history.", color: "from-brand-400 to-brand-600" },
    { icon: ClipboardList, title: "Specialty Classifier", text: "Your answers and history are analysed to pinpoint the right specialty — cardiology, neurology, general practice and more — with urgency level.", color: "from-teal-400 to-teal-600" },
    { icon: Users, title: "Provider Matcher", text: "A second agent searches doctors who have successfully treated similar symptoms and recommends your top 3–4 by fit, rating and availability.", color: "from-emerald-500 to-green-700" },
    { icon: CalendarCheck, title: "Instant booking", text: "Pick a doctor, choose an open slot that suits you and you're booked. Your doctor receives an AI pre-visit summary.", color: "from-lime-500 to-brand-600" },
  ];
  return (
    <section id="how" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-28 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <p className="font-semibold uppercase tracking-[0.2em] text-brand-600 text-xs">How it works</p>
        <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-brand-950 sm:text-5xl">A care team of AI agents, guided by real doctors</h2>
        <p className="mt-4 text-lg text-slate-600">Orchestrated agents hand off your case step by step — so you get to the right care, faster.</p>
      </div>
      <div className="relative mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <div className="absolute left-0 right-0 top-[52px] hidden h-0.5 bg-gradient-to-r from-transparent via-brand-300 to-transparent lg:block" />
        {steps.map((s, i) => (
          <motion.div key={s.title} variants={fadeUp} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="card group relative p-7 transition hover:-translate-y-1.5 hover:shadow-[0_24px_60px_-24px_rgba(4,120,87,0.45)]">
            <div className={`relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${s.color} text-white shadow-lg`}>
              <s.icon className="h-7 w-7" />
              <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-bold text-brand-700 shadow">{i + 1}</span>
            </div>
            <h3 className="mt-6 text-lg font-bold text-slate-900">{s.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-slate-600">{s.text}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function SpecialtiesSection() {
  return (
    <section id="specialties" className="relative scroll-mt-24 overflow-hidden bg-brand-950 py-28 text-white">
      <div className="absolute inset-0 opacity-[0.07] bg-grid" />
      <div className="absolute -right-40 -top-40 h-[480px] w-[480px] rounded-full bg-brand-500/30 blur-3xl" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid items-end gap-6 lg:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">Specialties</p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">Whatever you're feeling, we know who to call.</h2>
          </div>
          <p className="text-lg text-brand-100/80">From a lingering cough to heart palpitations, our classifier routes you to one of 13 specialties — and never replaces your doctor's judgement.</p>
        </div>
        <div className="mt-14 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {SPECIALTIES.map((s, i) => {
            const Icon = specialtyIcon(s);
            return (
              <motion.div key={s} variants={fadeUp} custom={i % 5} initial="hidden" whileInView="show" viewport={{ once: true }}
                className="group rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur transition hover:border-brand-400/50 hover:bg-white/10">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-500/20 text-brand-300 transition group-hover:bg-brand-400 group-hover:text-brand-950">
                  <Icon className="h-5 w-5" />
                </span>
                <p className="mt-4 font-semibold">{s}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function Team() {
  const people = [
    { img: "doctor-man", name: "Physicians", text: "Board-certified doctors across 13 specialties" },
    { img: "nurse-teal", name: "Nurses", text: "Caring nurses who follow up after every visit" },
    { img: "doctor-scan", name: "Specialists", text: "Experts in imaging, cardiology, neurology & more" },
  ];
  return (
    <section id="team" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-28 sm:px-6">
      <div className="grid items-center gap-14 lg:grid-cols-2">
        <div className="relative">
          <div className="overflow-hidden rounded-[2.5rem] border-[6px] border-white shadow-2xl shadow-brand-900/20">
            <img src="/images/doctor-patient.jpg" alt="Doctor talking with a patient" className="h-[460px] w-full object-cover" />
          </div>
          <div className="glass absolute -bottom-8 right-4 max-w-[260px] rounded-3xl p-5 sm:-right-6">
            <HeartHandshake className="h-7 w-7 text-brand-600" />
            <p className="mt-2 text-sm font-semibold text-slate-800">“The AI summary meant I spent our whole visit on care, not paperwork.”</p>
            <p className="mt-1 text-xs text-slate-500">— Partner physician</p>
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">Our care team</p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-brand-950 sm:text-5xl">Technology that brings you closer to people who care.</h2>
          <p className="mt-4 text-lg text-slate-600">Every recommendation leads to a real doctor or nurse. Before you arrive, your provider sees a concise pre-visit summary so you never have to repeat yourself.</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {people.map((p) => (
              <div key={p.name} className="card overflow-hidden">
                <img src={`/images/${p.img}.jpg`} alt={p.name} className="h-32 w-full object-cover" />
                <div className="p-4">
                  <p className="font-bold text-slate-900">{p.name}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">{p.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Features() {
  const items = [
    { icon: History, title: "Remembers your story", text: "Past conversations and history are kept securely, so every consultation builds on the last." },
    { icon: ShieldCheck, title: "Safety first", text: "Red-flag symptoms trigger immediate emergency guidance — no waiting, no guessing." },
    { icon: Lock, title: "Private by design", text: "Your data is encrypted in transit, never sold, and only shared with the doctor you book." },
  ];
  return (
    <section className="mx-auto max-w-7xl px-4 pb-28 sm:px-6">
      <div className="grid gap-6 md:grid-cols-3">
        {items.map((f, i) => (
          <motion.div key={f.title} variants={fadeUp} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }}
            className="rounded-3xl bg-gradient-to-br from-brand-50 to-white p-8 ring-1 ring-brand-600/10">
            <f.icon className="h-8 w-8 text-brand-600" />
            <h3 className="mt-5 text-xl font-bold text-slate-900">{f.title}</h3>
            <p className="mt-2 text-slate-600">{f.text}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function Stories() {
  const stories = [
    { name: "Priya S.", text: "I described my headaches and within minutes I had a neurologist who'd treated migraines like mine — booked for the next morning.", tag: "Neurology" },
    { name: "Marcus T.", text: "It remembered my diabetes and asked exactly the right questions. Felt like talking to a thoughtful nurse.", tag: "Endocrinology" },
    { name: "Elena R.", text: "When I mentioned chest pain spreading to my arm, it told me to call 911 immediately. That honesty matters.", tag: "Cardiology" },
  ];
  return (
    <section id="stories" className="scroll-mt-24 bg-gradient-to-b from-white to-brand-50/60 py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <h2 className="text-center font-display text-4xl font-semibold tracking-tight text-brand-950 sm:text-5xl">Loved by patients</h2>
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {stories.map((s, i) => (
            <motion.figure key={s.name} variants={fadeUp} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }} className="card p-8">
              <Quote className="h-8 w-8 text-brand-300" />
              <blockquote className="mt-4 text-[17px] leading-relaxed text-slate-700">{s.text}</blockquote>
              <figcaption className="mt-6 flex items-center justify-between">
                <span className="font-bold text-slate-900">{s.name}</span>
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">{s.tag}</span>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6">
      <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-brand-600 via-brand-700 to-teal-800 px-8 py-16 text-white sm:px-16">
        <PlusMark className="absolute -right-10 -top-10 h-56 w-56 rotate-12 opacity-15" glow={false} />
        <img src="/images/nurse-uniform.jpg" alt="" className="absolute inset-y-0 right-0 hidden h-full w-[34%] object-cover opacity-90 [mask-image:linear-gradient(to_right,transparent,black_40%)] lg:block" />
        <div className="relative max-w-xl">
          <h2 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">Feeling off? Let's find out who can help.</h2>
          <p className="mt-4 text-lg text-brand-50/90">Free to start. Takes about two minutes.</p>
          <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-7 py-4 font-semibold text-brand-800 shadow-xl transition hover:scale-[1.02]">
            Start my consultation <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-brand-900/10 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <Logo />
        <p className="max-w-xl text-xs leading-relaxed text-slate-500">
          Your Health Guide provides triage and appointment guidance and does not provide medical diagnosis or treatment.
          In an emergency call 911 or your local emergency number.
        </p>
        <p className="text-xs text-slate-400">© {new Date().getFullYear()} Your Health Guide</p>
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="overflow-x-hidden">
      <Navbar />
      <Hero />
      <Stats />
      <HowItWorks />
      <SpecialtiesSection />
      <Team />
      <Features />
      <Stories />
      <CTA />
      <Footer />
    </div>
  );
}
