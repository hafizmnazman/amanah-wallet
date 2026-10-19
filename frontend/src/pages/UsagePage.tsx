import { useQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { ErrorNote, MockBadge, PageTitle } from "@/components/common";
import { KancilSays } from "@/components/mascot/Kancil";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatTotal, formatUsdc } from "@/lib/usdc";
import { titleCase } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

/**
 * How each fund was used, for donors and the public (README sections 3 and 7.3): totals by programme and
 * month from GET /api/usage. It names no recipient and shows no wallet.
 */
export function UsagePage() {
  const { identity } = useIdentity();
  const usage = useQuery({ queryKey: ["usage"], queryFn: () => api.usage(identity) });
  const report = usage.data;

  return (
    <div className="space-y-5">
      <PageTitle title="How Each Fund Was Used" badges={<MockBadge />} />
      <KancilSays pose="happy" size={60}>
        Totals only: no recipient is named and no wallet is shown. A month with fewer than {report?.min_cell ?? 3} payouts
        shows how many there were, not how much, and a total that would give such a month away is not shown either.
        {report?.synthetic ? " The institution and its books are synthetic." : ""}
        {report?.source ? <span data-testid="usage-source"> Counted from {report.source}.</span> : null}
      </KancilSays>
      {usage.error && <ErrorNote error={usage.error} />}
      {report?.funds.map((fund) => (
        <Card key={fund.fund_code} data-testid="usage-fund">
          <CardHeader>
            <CardTitle>{fund.fund_name}</CardTitle>
            <CardDescription>
              {fund.total_usdc === null ? "Total paid out not shown" : `${formatTotal(fund.total_usdc)} paid out`};{" "}
              {formatUsdc(fund.donations_recorded_usdc)} USDC in recorded donations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {fund.programmes.map((p) => {
              const max = Math.max(1, ...p.by_month.map((m) => Number(m.total_usdc ?? 0)));
              return (
                <div key={p.programme_code} data-testid="usage-programme" className="space-y-3 rounded-2xl border-2 border-border bg-surface-2 p-4">
                  <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
                    <span className="text-base font-black">{titleCase(p.programme_name)}</span>
                    <span className="font-bold tabular-nums">{p.payouts} payouts</span>
                    <span className="font-bold tabular-nums">{p.households} households</span>
                    <span className="font-black tabular-nums text-success" data-testid="usage-total">
                      {formatTotal(p.total_usdc, "total not shown")}
                    </span>
                    <span className="font-bold text-muted">{p.paid_on_chain} paid on-chain</span>
                  </div>
                  {p.by_month.length > 0 && (
                    <ul className="space-y-1.5" aria-label={`${p.programme_name} by month`}>
                      {p.by_month.map((m) => {
                        const share = m.total_usdc === null ? 0 : Number(m.total_usdc) / max;
                        return (
                          <li key={m.month} className="grid grid-cols-[4.5rem_1fr_auto] items-center gap-3 text-sm">
                            <span className="font-bold tabular-nums text-muted">{m.month}</span>
                            <span className="h-4 overflow-hidden rounded-full border-2 border-border bg-surface">
                              <span className="block h-full rounded-full bg-primary" style={{ width: `${Math.max(share * 100, m.total_usdc === null ? 0 : 4)}%` }} />
                            </span>
                            <span className="font-extrabold tabular-nums">
                              {m.payouts} · {m.total_usdc === null ? "not shown" : formatUsdc(m.total_usdc)}
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
