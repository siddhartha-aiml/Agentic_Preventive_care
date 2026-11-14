import { Activity, Baby, Bone, Brain, Droplet, Ear, Eye, HeartPulse, Shield, Smile, Sparkles, Stethoscope, Wind, type LucideIcon } from "lucide-react";
import clsx from "clsx";

const ICONS: Record<string, LucideIcon> = {
  "General Physician": Stethoscope,
  Cardiology: HeartPulse,
  Neurology: Brain,
  Dermatology: Sparkles,
  Gastroenterology: Activity,
  Pulmonology: Wind,
  Orthopedics: Bone,
  ENT: Ear,
  Endocrinology: Droplet,
  Psychiatry: Smile,
  Ophthalmology: Eye,
  Urology: Shield,
  "Obstetrics & Gynecology": Baby,
};

export const specialtyIcon = (name?: string | null): LucideIcon => (name && ICONS[name]) || Stethoscope;

const URGENCY: Record<string, { label: string; cls: string }> = {
  routine: { label: "Routine", cls: "bg-brand-50 text-brand-700 ring-brand-600/20" },
  soon: { label: "See soon", cls: "bg-amber-50 text-amber-700 ring-amber-600/20" },
  urgent: { label: "Urgent", cls: "bg-orange-50 text-orange-700 ring-orange-600/25" },
  emergency: { label: "Emergency", cls: "bg-red-50 text-red-700 ring-red-600/25" },
};

export function UrgencyBadge({ urgency }: { urgency?: string | null }) {
  if (!urgency) return null;
  const u = URGENCY[urgency] ?? URGENCY.routine;
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset", u.cls)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {u.label}
    </span>
  );
}
