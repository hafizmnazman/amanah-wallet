import { Check } from "lucide-react";

import type { PlanCard } from "@/api";
import { MockBadge } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";
import { shortHex } from "@/lib/utils";

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
    <Card data-testid="plan-card" className={active ? "border-primary/50" : "opacity-80"}>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>
            {card.fund_name}: {card.programme_name}
          </CardTitle>
          <Badge variant="muted">{card.programme_code}</Badge>
          <MockBadge />
        </div>
        <CardDescription>
          Batch {card.batch_id}, {card.items.length} households
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted">
              <tr>
                <th className="py-1 pr-3 font-medium">Household</th>
                <th className="py-1 pr-3 font-medium">Beneficiary</th>
                <th className="hidden py-1 pr-3 font-medium sm:table-cell">Wallet</th>
                <th className="py-1 text-right font-medium">Amount (USDC)</th>
              </tr>
            </thead>
            <tbody>
              {card.items.map((item) => (
                <tr key={item.household_ref} data-testid="plan-row" className="border-t border-border/60">
                  <td className="py-1.5 pr-3">{item.household_ref}</td>
                  <td className="py-1.5 pr-3">{item.beneficiary_ref}</td>
                  <td className="hash hidden py-1.5 pr-3 text-xs text-muted sm:table-cell">{shortHex(item.wallet)}</td>
                  <td className="py-1.5 text-right tabular-nums">{formatUsdc(item.amount_usdc)}</td>
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
        <div className="text-sm">
          Total <span data-testid="plan-total" className="font-semibold tabular-nums">{formatUsdc(card.total_usdc)}</span> USDC
        </div>
        <Badge variant={elevated ? "warning" : "success"} data-testid="tier-preview">
          {elevated ? "Elevated: a trustee co-signs" : "Routine: no human needed"}
        </Badge>
        {active && (
          <Button className="ml-auto" onClick={onConfirm} disabled={busy}>
            <Check className="h-4 w-4" aria-hidden />
            Confirm {card.items.length} payouts
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
