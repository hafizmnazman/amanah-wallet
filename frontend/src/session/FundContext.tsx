import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { PROGRAMMES, type Programme } from "@/lib/programmes";
import { safeStorage } from "@/lib/utils";

/** The fund and programme the officer is working in (task D6). The chat defaults to it. */
interface FundState {
  programme: Programme;
  programmes: Programme[];
  setProgramme: (code: string) => void;
}

const FundContext = createContext<FundState | null>(null);
const STORAGE_KEY = "amanah.programme";

export function FundProvider({ children }: { children: ReactNode }) {
  const [code, setCode] = useState<string>(() => safeStorage.get(STORAGE_KEY) ?? PROGRAMMES[0].code);
  const value = useMemo<FundState>(
    () => ({
      programme: PROGRAMMES.find((p) => p.code === code) ?? PROGRAMMES[0],
      programmes: PROGRAMMES,
      setProgramme: (next) => {
        safeStorage.set(STORAGE_KEY, next);
        setCode(next);
      },
    }),
    [code],
  );
  return <FundContext.Provider value={value}>{children}</FundContext.Provider>;
}

export function useFund(): FundState {
  const state = useContext(FundContext);
  if (!state) throw new Error("useFund needs a FundProvider");
  return state;
}
