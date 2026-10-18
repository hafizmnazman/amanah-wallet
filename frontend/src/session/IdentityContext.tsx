import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { Identity, Role } from "@/api";
import { safeStorage } from "@/lib/utils";

/** Who the demo is acting as. The backend reads it from X-Amanah-Role and X-Amanah-User. */
export const ROLES: { role: Role; label: string; user: string }[] = [
  { role: "finance_officer", label: "Finance officer", user: "officer-1" },
  { role: "trustee", label: "Trustee", user: "trustee-1" },
  { role: "guardian", label: "Guardian", user: "guardian-1" },
  { role: "external_auditor", label: "External auditor", user: "auditor-1" },
];

interface IdentityState {
  identity: Identity;
  setRole: (role: Role) => void;
}

const IdentityContext = createContext<IdentityState | null>(null);
const STORAGE_KEY = "amanah.role";

function initialRole(): Role {
  const stored = safeStorage.get(STORAGE_KEY);
  return ROLES.some((r) => r.role === stored) ? (stored as Role) : "finance_officer";
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(initialRole);
  const value = useMemo<IdentityState>(() => {
    const entry = ROLES.find((r) => r.role === role) ?? ROLES[0];
    return {
      identity: { role: entry.role, user: entry.user },
      setRole: (next) => {
        safeStorage.set(STORAGE_KEY, next);
        setRoleState(next);
      },
    };
  }, [role]);
  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}

export function useIdentity(): IdentityState {
  const state = useContext(IdentityContext);
  if (!state) throw new Error("useIdentity needs an IdentityProvider");
  return state;
}
