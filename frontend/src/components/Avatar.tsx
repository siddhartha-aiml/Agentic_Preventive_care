import { useState } from "react";
import clsx from "clsx";

const GRADS = ["from-emerald-400 to-teal-600", "from-teal-400 to-cyan-600", "from-lime-400 to-emerald-600", "from-green-400 to-emerald-700"];

export default function Avatar({ name, src, className }: { name: string; src?: string | null; className?: string }) {
  const [failed, setFailed] = useState(false);
  const initials = name.replace(/^Dr\.\s*/, "").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase();
  const grad = GRADS[name.length % GRADS.length];
  if (src && !failed) {
    return <img src={src} alt={name} onError={() => setFailed(true)} className={clsx("rounded-2xl object-cover", className)} loading="lazy" />;
  }
  return (
    <div className={clsx("flex items-center justify-center rounded-2xl bg-gradient-to-br font-bold text-white", grad, className)}>{initials}</div>
  );
}
