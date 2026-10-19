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
  { to: "/officer", label: "Officer", icon: MessagesSquare, tint: "text-planner", end: false },
  { to: "/trustee", label: "Trustee", icon: KeyRound, tint: "text-sentinel-dark", end: false },
  { to: "/redteam", label: "Red team", icon: ShieldCheck, tint: "text-danger", end: false },
  { to: "/proof", label: "Proof", icon: Link2, tint: "text-sky-dark", end: false },
  { to: "/queue", label: "Queue", icon: Hourglass, tint: "text-auditor", end: false },
  { to: "/usage", label: "Fund use", icon: HandHeart, tint: "text-primary", end: false },
];

/**
 * One navigation block: a top bar on a phone, a sidebar from 1024 px. It is rendered once, so the role and
 * fund pickers exist once on the page.
 */
export function Layout() {
  const { identity, setRole } = useIdentity();
  const { programme, programmes, setProgramme } = useFund();

  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b-2 border-border bg-surface lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:shrink-0 lg:border-b-0 lg:border-r-2">
        <div className="flex flex-col gap-3 p-3 lg:h-full lg:gap-6 lg:overflow-y-auto lg:p-5">
          <NavLink to="/" className="flex items-center gap-2.5" aria-label="Amanah home">
            <Kancil pose="calm" size={44} title="Sang Kancil" />
            <span className="flex flex-col leading-none">
              <span className="text-2xl font-black tracking-tight text-primary">amanah</span>
              <span className="text-[11px] font-bold text-muted">money held in trust</span>
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
                    "flex items-center gap-2 rounded-2xl border-2 px-2.5 py-1.5 text-xs font-extrabold uppercase tracking-wide transition-colors lg:gap-3 lg:px-3 lg:py-2.5 lg:text-sm",
                    isActive ? "border-sky/50 bg-sky-light text-sky-dark" : "border-transparent text-muted hover:bg-surface-2 hover:text-ink",
                  )
                }
              >
                <Icon className={cn("h-4 w-4 lg:h-5 lg:w-5", tint)} strokeWidth={2.6} aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex flex-col gap-2 sm:flex-row lg:mt-auto lg:flex-col lg:rounded-2xl lg:border-2 lg:border-border lg:bg-surface-2 lg:p-3">
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] font-extrabold uppercase tracking-wide text-muted">
              Acting as
              <Select aria-label="Role" value={identity.role} onChange={(e) => setRole(e.target.value as Role)} className="min-w-0 bg-surface">
                {ROLES.map((r) => (
                  <option key={r.role} value={r.role}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </label>
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-[11px] font-extrabold uppercase tracking-wide text-muted">
              Fund
              <Select
                aria-label="Fund and programme"
                value={programme.code}
                onChange={(e) => setProgramme(e.target.value)}
                className="min-w-0 bg-surface"
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
