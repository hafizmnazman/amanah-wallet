import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ShieldX } from "lucide-react";
import { useMemo } from "react";
import { privateKeyToAccount } from "viem/accounts";
import { useAccount, useSignTypedData, useSwitchChain } from "wagmi";

import { api, type PendingPayout } from "@/api";
import { MOCK_VAULT } from "@/api/mockData";
import { ErrorNote, MockBadge, VerdictBadge } from "@/components/common";
import { SIGNER_LABELS } from "@/components/plan/VerdictCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { config } from "@/config";
import { checkSummary } from "@/lib/summaryCheck";
import { checkTypedData, decodePayout, toSignable, type DecodedPayout } from "@/lib/typedData";
import { useIdentity } from "@/session/IdentityContext";

/** The vault a payout must name. In mock mode without VITE_VAULT_ADDRESS, the mock's own vault. */
export const expectedVault = config.vaultAddress || (api.isMock ? MOCK_VAULT : "");

/**
 * One elevated payout for a trustee (task D3): the planner's plain-words summary beside the fields the
 * wallet will sign, decoded from the typed data itself, with every mismatch shown before signing.
 */
export interface SignedPayout {
  proposalId: string;
  summary: string;
  txHash: string;
  status: string;
  signedBy: string | null;
}

export function PendingPayoutCard({ item, onSigned }: { item: PendingPayout; onSigned: (signed: SignedPayout) => void }) {
  const { identity } = useIdentity();
  const queryClient = useQueryClient();
  const account = useAccount();
  const { switchChainAsync } = useSwitchChain();
  const { signTypedDataAsync } = useSignTypedData();

  const decoded = useMemo((): { payout: DecodedPayout | null; error: string | null } => {
    try {
      return { payout: decodePayout(item.typed_data), error: null };
    } catch (e) {
      return { payout: null, error: e instanceof Error ? e.message : String(e) };
    }
  }, [item.typed_data]);
  const domainCheck = checkTypedData(item.typed_data, { chainId: config.chainId, vaultAddress: expectedVault });
  const summaryCheck = decoded.payout ? checkSummary(item.summary_text, decoded.payout) : { ok: false, problems: [] };
  const safe = decoded.payout !== null && domainCheck.ok && summaryCheck.ok;

  const submit = useMutation({
    mutationFn: async (signer: "wallet" | "dev") => {
      const signable = toSignable(item.typed_data);
      let signature: `0x${string}`;
      let signedBy: string | null = null;
      if (signer === "dev") {
        if (!config.devTrusteeKey) throw new Error("VITE_DEV_TRUSTEE_KEY is not set.");
        const local = privateKeyToAccount(config.devTrusteeKey);
        signature = await local.signTypedData(signable);
        signedBy = local.address;
      } else {
        if (!account.isConnected) throw new Error("Connect the trustee wallet first.");
        if (account.chainId !== signable.domain.chainId) await switchChainAsync({ chainId: signable.domain.chainId });
        signature = await signTypedDataAsync(signable);
        signedBy = account.address ?? null;
      }
      const result = await api.trusteeSign(identity, { proposal_id: item.proposal_id, signature });
      onSigned({ proposalId: item.proposal_id, summary: item.summary_text, txHash: result.tx_hash, status: result.status, signedBy });
      return result;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["pending"] }),
  });

  return (
    <Card data-testid="pending-payout">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>Elevated payout</CardTitle>
          <Badge variant="warning">Tier {String(item.tier)}</Badge>
          <MockBadge />
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-2">
        <section aria-label="Summary">
          <h4 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">What the planner says</h4>
          <p className="text-sm leading-relaxed" data-testid="summary-text">
            {item.summary_text}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(Object.keys(SIGNER_LABELS) as (keyof typeof SIGNER_LABELS)[]).map((signer) => (
              <span key={signer} className="inline-flex items-center gap-1 text-xs">
                {SIGNER_LABELS[signer]} <VerdictBadge verdict={item.verdicts[signer].verdict} />
              </span>
            ))}
          </div>
        </section>
        <section aria-label="Fields you sign">
          <h4 className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">What you sign (decoded from the typed data)</h4>
          {decoded.payout ? (
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm" data-testid="decoded-fields">
              {decoded.payout.rows.map((row) => (
                <div key={row.field} className="contents">
                  <dt className="text-muted">{row.label}</dt>
                  <dd className="hash" data-testid={`field-${row.field}`}>
                    {row.value}
                  </dd>
                </div>
              ))}
              <dt className="text-muted">Chain</dt>
              <dd className="hash">{String(item.typed_data.domain.chainId)}</dd>
              <dt className="text-muted">Vault</dt>
              <dd className="hash">{item.typed_data.domain.verifyingContract}</dd>
            </dl>
          ) : (
            <ErrorNote error={`The typed data cannot be decoded: ${decoded.error}`} />
          )}
        </section>
        <section className="lg:col-span-2" aria-label="Checks">
          {safe ? (
            <p className="flex items-center gap-2 text-sm text-success" data-testid="checks-ok">
              <ShieldCheck className="h-4 w-4" aria-hidden />
              The summary matches the signed fields, and the domain names this vault on chain {config.chainId}.
            </p>
          ) : (
            <div role="alert" data-testid="checks-failed" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              <p className="flex items-center gap-2 font-medium">
                <ShieldX className="h-4 w-4" aria-hidden />
                Do not sign. What you would sign does not match.
              </p>
              <ul className="mt-1 list-disc pl-5">
                {[...domainCheck.problems, ...summaryCheck.problems].map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </CardContent>
      <CardFooter>
        <Button disabled={!safe || submit.isPending} onClick={() => submit.mutate("wallet")}>
          Sign in MetaMask
        </Button>
        {config.devSigning && (
          <Button variant="secondary" disabled={!safe || submit.isPending} onClick={() => submit.mutate("dev")}>
            Sign with local trustee key
          </Button>
        )}
        {submit.error && <ErrorNote error={submit.error} />}
      </CardFooter>
    </Card>
  );
}
