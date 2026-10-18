import { NavLink, Outlet } from "react-router";

import type { Role } from "@/api";
import { MockBadge } from "@/components/common";
import { PostureBanner } from "@/components/PostureBanner";
import { Select } from "@/components/ui/fields";
import { cn } from "@/lib/utils";
import { useFund } from "@/session/FundContext";
import { ROLES, useIdentity } from "@/session/IdentityContext";

const NAV = [
  { to: "/officer", label: "Officer" },
  { to: "/trustee", label: "Trustee" },
  { to: "/queue", label: "Queue" },
  { to: "/proof", label: "Proof" },
  { to: "/usage", label: "Fund use" },
];

export function Layout() {
  const { identity, setRole } = useIdentity();
  const { programme, programmes, setProgramme } = useFund();

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-surface/60">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold tracking-wide text-primary">Amanah</span>
            <MockBadge />
          </div>
          <nav aria-label="Main" className="flex flex-wrap gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn("rounded-md px-3 py-1.5 text-sm", isActive ? "bg-surface-2 text-foreground" : "text-muted hover:text-foreground")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex w-full flex-col gap-2 sm:ml-auto sm:w-auto sm:flex-row sm:gap-3">
            <label className="flex min-w-0 items-center gap-2 text-xs text-muted">
              Fund
              <Select
                aria-label="Fund and programme"
                value={programme.code}
                onChange={(e) => setProgramme(e.target.value)}
                className="min-w-0 flex-1 sm:w-64 sm:flex-none"
              >
                {programmes.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.fund}: {p.name} ({p.code})
                  </option>
                ))}
              </Select>
            </label>
            <label className="flex min-w-0 items-center gap-2 text-xs text-muted">
              Acting as
              <Select aria-label="Role" value={identity.role} onChange={(e) => setRole(e.target.value as Role)} className="min-w-0 flex-1 sm:w-40 sm:flex-none">
                {ROLES.map((r) => (
                  <option key={r.role} value={r.role}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </label>
          </div>
        </div>
      </header>
      <PostureBanner />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
