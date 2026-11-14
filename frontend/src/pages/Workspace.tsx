import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useMatch, useNavigate, useOutletContext } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarCheck, FileHeart, LogOut, Menu, MessageSquare, Plus, Trash2, X } from "lucide-react";
import clsx from "clsx";
import Logo from "../components/Logo";
import { specialtyIcon } from "../components/specialty";
import { api, type Conversation, type Meta } from "../lib/api";
import { useAuth } from "../lib/auth";

export interface WorkspaceCtx {
  conversations: Conversation[];
  refresh: () => Promise<void>;
  upsert: (c: Conversation) => void;
  meta: Meta | null;
}

export const useWorkspace = () => useOutletContext<WorkspaceCtx>();

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso + (iso.endsWith("Z") ? "" : "Z")).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function Workspace() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const activeId = useMatch("/app/c/:id")?.params.id;
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    setConversations(await api.conversations());
  }, []);
  const upsert = useCallback((c: Conversation) => {
    setConversations((cs) => [c, ...cs.filter((x) => x.id !== c.id)]);
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
    api.meta().then(setMeta).catch(() => {});
  }, [refresh]);

  const remove = async (id: string) => {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;
    await api.deleteConversation(id);
    setConversations((cs) => cs.filter((c) => c.id !== id));
    if (id === activeId) nav("/app");
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-5 pb-4 pt-5">
        <Logo to="/" />
        <button className="rounded-full p-1.5 text-slate-500 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
      </div>
      <div className="px-4">
        <button onClick={() => { nav("/app"); setOpen(false); }} className="btn-primary w-full !py-3"><Plus className="h-4 w-4" /> New consultation</button>
      </div>
      <nav className="mt-5 space-y-1 px-3">
        {[
          ["/app/appointments", "Appointments", CalendarCheck],
          ["/app/profile", "Health profile", FileHeart],
        ].map(([to, label, Icon]: any) => (
          <NavLink key={to} to={to} onClick={() => setOpen(false)}
            className={({ isActive }) => clsx("flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-semibold transition",
              isActive ? "bg-brand-50 text-brand-800" : "text-slate-600 hover:bg-slate-50")}>
            <Icon className="h-4 w-4" /> {label}
          </NavLink>
        ))}
      </nav>
      <p className="mt-6 px-6 text-[11px] font-bold uppercase tracking-[0.15em] text-slate-400">Past conversations</p>
      <div className="scrollbar-thin mt-2 flex-1 space-y-1 overflow-y-auto px-3 pb-3">
        {conversations.length === 0 && <p className="px-3 py-4 text-sm text-slate-400">No conversations yet.</p>}
        {conversations.map((c) => {
          const Icon = c.specialty ? specialtyIcon(c.specialty) : MessageSquare;
          return (
            <div key={c.id} className={clsx("group flex items-center gap-2 rounded-2xl px-3 py-2.5 transition",
              c.id === activeId ? "bg-brand-50 ring-1 ring-brand-600/15" : "hover:bg-slate-50")}>
              <button onClick={() => { nav(`/app/c/${c.id}`); setOpen(false); }} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                <span className={clsx("flex h-8 w-8 shrink-0 items-center justify-center rounded-xl", c.specialty ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500")}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-800">{c.title}</span>
                  <span className="block truncate text-xs text-slate-400">{c.specialty ?? "In progress"} · {timeAgo(c.updated_at)}</span>
                </span>
              </button>
              <button onClick={() => remove(c.id)} className="rounded-lg p-1 text-slate-300 opacity-0 transition hover:text-red-500 group-hover:opacity-100" aria-label="Delete conversation">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
      <div className="border-t border-slate-100 p-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-teal-600 font-bold text-white">
            {user?.full_name.split(" ").map((s) => s[0]).slice(0, 2).join("")}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-800">{user?.full_name}</p>
            <p className="truncate text-xs text-slate-400">{user?.email}</p>
          </div>
          <button onClick={() => { logout(); nav("/"); }} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-dvh overflow-hidden bg-mint">
      <aside className="hidden w-80 shrink-0 border-r border-emerald-900/5 bg-white lg:block">{sidebar}</aside>
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="fixed inset-0 z-40 bg-brand-950/30 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} />
            <motion.aside className="fixed inset-y-0 left-0 z-50 w-80 max-w-[85vw] bg-white shadow-2xl lg:hidden"
              initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }} transition={{ type: "spring", damping: 28, stiffness: 300 }}>
              {sidebar}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
      <main className="relative flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-emerald-900/5 bg-white/80 px-4 py-3 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} className="rounded-xl p-2 text-slate-600" aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <Logo compact />
          <span className="w-9" />
        </div>
        {meta?.agent_mode === "demo" && (
          <div className="bg-amber-50 px-4 py-1.5 text-center text-xs font-medium text-amber-800">
            Demo mode — rule-based agents are active. Set <code className="font-mono">OPENAI_API_KEY</code> to enable GPT-powered agents.
          </div>
        )}
        {meta?.agent_mode === "degraded" && (
          <div className="bg-red-50 px-4 py-1.5 text-center text-xs font-medium text-red-800">
            The AI service is having trouble right now ({meta.llm_last_error_type}) — backup rule-based agents are answering.
          </div>
        )}
        <Outlet context={{ conversations, refresh, upsert, meta } satisfies WorkspaceCtx} />
      </main>
    </div>
  );
}
