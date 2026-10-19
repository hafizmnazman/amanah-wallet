import { HandHeart, Hourglass, House, KeyRound, Link2, MessagesSquare, ShieldCheck } from "lucide-react";
import { NavLink, Outlet } from "react-router";

import type { Role } from "@/api";
import { MockBadge } from "@/components/common";
import { Kancil } from "@/components/mascot/Kancil";
import { PostureBanner } from "@/components/PostureBanner";
import { Select } from "@/components/ui/fields";
import { cn } from "@/lib/utils";
import { useFund } from "@/session/FundContext";
import { ROLES, useIdentity } from "@/session/IdentityContext";

const NAV = [
  { to: "/", label: "Home", icon: House, tint: "text-kancil-dark", end: true },
  { to: "/officer", label: "Officer desk", icon: MessagesSquare, tint: "text-planner", end: false },
  { to: "/trustee", label: "Trustee", icon: KeyRound, tint: "text-gold-dark", end: false },
  { to: "/redteam", label: "Red team", icon: ShieldCheck, tint: "text-danger", end: false },
  { to: "/proof", label: "On-chain proof", icon: Link2, tint: "text-primary", end: false },
  { to: "/queue", label: "Queue", icon: Hourglass, tint: "text-auditor", end: false },
  { to: "/usage", label: "Fund use", icon: HandHeart, tint: "text-sentinel-dark", end: false },
];

/**
 * One navigation block: a navy top bar on a phone, a navy sidebar from 1024 px. It is rendered once, so the
 * role and fund pickers exist once on the page.
 */
export function Layout() {
  const { identity, setRole } = useIdentity();
  const { programme, programmes, setProgramme } = useFund();

  return (
    <div className="min-h-screen lg:flex">
      <aside className="bg-navy text-white lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:shrink-0">
        <div className="flex flex-col gap-3 p-3 lg:h-full lg:gap-6 lg:overflow-y-auto lg:p-5">
          <NavLink to="/" className="flex items-center gap-3" aria-label="Amanah home">
            <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white shadow-[0_3px_0_rgba(0,0,0,0.25)]">
              <Kancil pose="calm" size={40} title="Sang Kancil" />
            </span>
            <span className="flex flex-col leading-none">
              <span className="font-display text-2xl font-extrabold tracking-tight text-white">amanah</span>
              <span className="mt-1 text-[11px] font-semibold text-white/60">money held in trust</span>
            </span>
            <MockBadge className="ml-1" />
          </NavLink>
          <nav aria-label="Main" className="flex flex-wrap gap-1.5 lg:flex-col lg:gap-1">
            {NAV.map(({ to, label, icon: Icon, tint, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-xl border-2 px-2.5 py-1.5 text-xs font-bold transition-colors lg:gap-3 lg:px-3 lg:py-2.5 lg:text-sm",
                    isActive
                      ? "border-white border-b-[4px] border-b-white/70 bg-white text-navy"
                      : "border-transparent text-white/75 hover:bg-white/10 hover:text-white",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={cn("h-4 w-4 lg:h-5 lg:w-5", isActive ? tint : "text-white/70")} strokeWidth={2.4} aria-hidden />
                    {label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="flex flex-col gap-2 sm:flex-row lg:mt-auto lg:flex-col lg:rounded-2xl lg:border-2 lg:border-white/10 lg:bg-white/5 lg:p-3">
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] font-bold uppercase tracking-wide text-white/65">
              Acting as
              <Select aria-label="Role" value={identity.role} onChange={(e) => setRole(e.target.value as Role)} className="min-w-0 border-white/20 bg-white">
                {ROLES.map((r) => (
                  <option key={r.role} value={r.role}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </label>
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] font-bold uppercase tracking-wide text-white/65">
              Fund
              <Select
                aria-label="Fund and programme"
                value={programme.code}
                onChange={(e) => setProgramme(e.target.value)}
                className="min-w-0 border-white/20 bg-white"
              >
                {programmes.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.fund}: {p.name} ({p.code})
                  </option>
                ))}
              </Select>
            </label>
          </div>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <PostureBanner />
        <main className="mx-auto max-w-5xl px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
