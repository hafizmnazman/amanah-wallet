import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";
import { useState } from "react";

import { api, type PayoutResult, type ScheduledDraft } from "@/api";
import { ErrorNote } from "@/components/common";
import { useIdentity } from "@/session/IdentityContext";

import { PayoutResults } from "./PayoutResults";
import { PlanCardView } from "./PlanCardView";

/**
 * Batches the books schedule, drafted by the backend for the officer (plan task B11). Nothing is paid until
 * the officer presses Confirm; the checks then run as for any other plan.
 */
export function ScheduledDrafts() {
  const { identity } = useIdentity();
  const queryClient = useQueryClient();
  const [results, setResults] = useState<PayoutResult[] | null>(null);
  const drafts = useQuery({
    queryKey: ["scheduled", identity.role, identity.user],
    queryFn: () => api.scheduled(identity),
    enabled: identity.role === "finance_officer",
    refetchInterval: 60_000,
  });
  const confirm = useMutation({
    mutationFn: (d: ScheduledDraft) => api.confirm(identity, { session_id: d.session_id, batch_id: d.plan_card.batch_id }),
    onSuccess: (r) => {
      setResults(r.results);
      void queryClient.invalidateQueries({ queryKey: ["scheduled"] });
    },
  });
  const items = drafts.data?.items ?? [];
  if (items.length === 0 && !results) return null;
  return (
    <section className="space-y-3" data-testid="scheduled-drafts" aria-label="Scheduled batches">
      <h2 className="flex items-center gap-2 text-base font-black">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border-2 border-sky/40 bg-sky-light text-sky-dark">
          <CalendarClock className="h-4.5 w-4.5" aria-hidden />
        </span>
        Scheduled by the books, waiting for your confirmation
      </h2>
      {items.map((d) => (
        <PlanCardView key={d.session_id} card={d.plan_card} active busy={confirm.isPending} onConfirm={() => confirm.mutate(d)} />
      ))}
      <ErrorNote error={confirm.error} />
      {results && <PayoutResults results={results} />}
    </section>
  );
}
