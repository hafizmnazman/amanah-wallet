import { useQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { ErrorNote, MockBadge } from "@/components/common";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatTotal, formatUsdc } from "@/lib/usdc";
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold">How each fund was used</h1>
        <MockBadge />
      </div>
      <p className="text-sm text-muted">
        Totals only: no recipient is named and no wallet is shown. A month with fewer than {report?.min_cell ?? 3} payouts
        shows how many there were, not how much, and a total that would give such a month away is not shown either.{report?.synthetic ? " The institution and its books are synthetic." : ""}
        {report?.source ? <span data-testid="usage-source"> Counted from {report.source}.</span> : null}
      </p>
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
          <CardContent className="space-y-3">
            {fund.programmes.map((p) => (
              <div key={p.programme_code} data-testid="usage-programme" className="space-y-2">
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
                  <span className="font-medium">{p.programme_name}</span>
                  <span className="tabular-nums">{p.payouts} payouts</span>
                  <span className="tabular-nums">{p.households} households</span>
                  <span className="tabular-nums" data-testid="usage-total">{formatTotal(p.total_usdc, "total not shown")}</span>
                  <span className="text-muted">{p.paid_on_chain} paid on-chain</span>
                </div>
                {p.by_month.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full max-w-md text-sm">
                      <thead className="text-left text-xs text-muted">
                        <tr>
                          <th className="py-1 pr-4 font-medium">Month</th>
                          <th className="py-1 pr-4 font-medium">Payouts</th>
                          <th className="py-1 font-medium">USDC</th>
                        </tr>
                      </thead>
                      <tbody>
                        {p.by_month.map((m) => (
                          <tr key={m.month} className="border-t border-border/60">
                            <td className="py-1 pr-4 tabular-nums">{m.month}</td>
                            <td className="py-1 pr-4 tabular-nums">{m.payouts}</td>
                            <td className="py-1 tabular-nums">{m.total_usdc === null ? "not shown" : formatUsdc(m.total_usdc)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
