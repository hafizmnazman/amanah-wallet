import { Check, KeyRound, Zap } from "lucide-react";

import type { PlanCard } from "@/api";
import { MockBadge } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";
import { cn, shortHex, titleCase } from "@/lib/utils";

/** One confirmation card for a whole batch (task D2). */
export function PlanCardView({
  card,
  active,
  busy,
  onConfirm,
}: {
  card: PlanCard;
  active: boolean;
  busy: boolean;
  onConfirm: () => void;
}) {
  const elevated = card.tier_preview === "elevated";
  return (
    <Card data-testid="plan-card" className={cn("animate-pop", active ? "border-primary/50 border-b-primary/60" : "opacity-60")}>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>
            {card.fund_name}: {titleCase(card.programme_name)}
          </CardTitle>
          <Badge variant="muted">{card.programme_code}</Badge>
          <MockBadge />
        </div>
        <CardDescription>
          Batch {card.batch_id}, {card.items.length} households
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto rounded-2xl border-2 border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-[11px] font-extrabold uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2">Household</th>
                <th className="px-3 py-2">Beneficiary</th>
                <th className="hidden px-3 py-2 sm:table-cell">Wallet</th>
                <th className="px-3 py-2 text-right">Amount (USDC)</th>
              </tr>
            </thead>
            <tbody>
              {card.items.map((item) => (
                <tr key={item.household_ref} data-testid="plan-row" className="border-t-2 border-border/70">
                  <td className="px-3 py-2 font-extrabold">{item.household_ref}</td>
                  <td className="px-3 py-2 text-muted">{item.beneficiary_ref}</td>
                  <td className="hash hidden px-3 py-2 text-xs text-muted sm:table-cell">{shortHex(item.wallet)}</td>
                  <td className="px-3 py-2 text-right font-extrabold tabular-nums">{formatUsdc(item.amount_usdc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {card.notes.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted">
            {card.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}
      </CardContent>
      <CardFooter>
        <div className="text-sm font-bold text-muted">
          Total{" "}
          <span data-testid="plan-total" className="text-2xl font-black tabular-nums text-ink">
            {formatUsdc(card.total_usdc)}
          </span>{" "}
          USDC
        </div>
        <Badge variant={elevated ? "warning" : "success"} data-testid="tier-preview">
          {elevated ? <KeyRound className="h-3.5 w-3.5" aria-hidden /> : <Zap className="h-3.5 w-3.5" aria-hidden />}
          {elevated ? "Elevated: A Trustee Co-Signs" : "Routine: No Human Needed"}
        </Badge>
        {active && (
          <Button className="w-full sm:ml-auto sm:w-auto" onClick={onConfirm} disabled={busy}>
            <Check className="h-5 w-5" strokeWidth={3} aria-hidden />
            Confirm {card.items.length} Payouts
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
