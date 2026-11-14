import { Link } from "react-router-dom";
import clsx from "clsx";

export function PlusMark({ className, glow = true }: { className?: string; glow?: boolean }) {
  return (
    <span className={clsx("relative inline-flex shrink-0", className)}>
      {glow && <span className="absolute inset-0 rounded-[30%] bg-brand-400/50 blur-md" />}
      <svg viewBox="0 0 64 64" className="relative h-full w-full drop-shadow-sm" aria-hidden>
        <defs>
          <linearGradient id="yhg-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#34d399" />
            <stop offset="1" stopColor="#047857" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="18" fill="url(#yhg-g)" />
        <path
          d="M26 12h12a2 2 0 0 1 2 2v12h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H40v12a2 2 0 0 1-2 2H26a2 2 0 0 1-2-2V38H12a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h12V14a2 2 0 0 1 2-2z"
          fill="#fff"
        />
      </svg>
    </span>
  );
}

export default function Logo({ to = "/", light = false, compact = false }: { to?: string; light?: boolean; compact?: boolean }) {
  return (
    <Link to={to} className="group inline-flex items-center gap-2.5" aria-label="Your Health Guide home">
      <PlusMark className="h-9 w-9 transition-transform duration-300 group-hover:rotate-90" />
      {!compact && (
        <span className={clsx("font-display text-xl font-semibold tracking-tight", light ? "text-white" : "text-brand-950")}>
          Your Health <span className={light ? "text-brand-300" : "text-brand-600"}>Guide</span>
        </span>
      )}
    </Link>
  );
}
