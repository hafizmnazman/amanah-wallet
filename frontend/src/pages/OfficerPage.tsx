import { X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { RoleHint } from "@/components/common";
import { ScheduledDrafts } from "@/components/plan/ScheduledDrafts";
import { safeStorage } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

const STEPS_KEY = "amanah.officer-steps";

function StepNumber({ n }: { n: number }) {
  return (
    <span className="mr-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-black text-white" aria-hidden>
      {n}
    </span>
  );
}

/** Three steps for a first visit, until dismissed; the choice is remembered in this browser. */
function FirstVisitSteps() {
  const [hidden, setHidden] = useState(() => safeStorage.get(STEPS_KEY) === "hidden");
  if (hidden) return null;
  return (
    <div
      className="flex items-center gap-3 rounded-2xl border-2 border-primary/30 bg-primary-light px-4 py-2 text-sm font-bold text-primary-dark"
      data-testid="first-visit"
    >
      <ol className="flex flex-1 flex-wrap items-center gap-x-2 gap-y-1" aria-label="Three steps to try">
        <li>
          <StepNumber n={1} />
          Confirm the batch
        </li>
        <li aria-hidden>·</li>
        <li>
          <StepNumber n={2} />
          Try a trick
        </li>
        <li aria-hidden>·</li>
        <li>
          <StepNumber n={3} />
          <Link to="/redteam" className="underline underline-offset-2 hover:text-primary">
            See the red team
          </Link>
        </li>
      </ol>
      <button
        type="button"
        aria-label="Hide These Steps"
        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full hover:bg-white/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky"
        onClick={() => {
          safeStorage.set(STEPS_KEY, "hidden");
          setHidden(true);
        }}
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}

export function OfficerPage() {
  const { identity } = useIdentity();
  return (
    <div className="space-y-4">
      <FirstVisitSteps />
      <RoleHint expected={identity.role === "finance_officer"} label="finance officers" role="finance_officer" />
      <ScheduledDrafts />
      <ChatPanel />
    </div>
  );
}
