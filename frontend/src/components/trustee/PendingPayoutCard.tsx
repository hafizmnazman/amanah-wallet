import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, ReceiptText } from "lucide-react";
import { useMemo } from "react";
import { privateKeyToAccount } from "viem/accounts";
import { useAccount, useSignTypedData, useSwitchChain } from "wagmi";

import { api, type PendingPayout } from "@/api";
import { MOCK_VAULT } from "@/api/mockData";
import { ErrorNote, MockBadge, VerdictBadge } from "@/components/common";
import { Kancil } from "@/components/mascot/Kancil";
import { SIGNER_LABELS } from "@/components/plan/VerdictCard";
import { SignerAvatar } from "@/components/signers";
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
    <Card data-testid="pending-payout" className="animate-pop">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border-2 border-sentinel-dark border-b-4 bg-sentinel text-white">
            <KeyRound className="h-5 w-5" strokeWidth={2.6} aria-hidden />
          </span>
          <CardTitle>Elevated payout</CardTitle>
          <Badge variant="warning">Tier {String(item.tier)}</Badge>
          <MockBadge />
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-2">
        <section aria-label="Summary" className="space-y-3">
          <h4 className="text-xs font-extrabold uppercase tracking-wide text-muted">What the planner says</h4>
          <div className="flex items-start gap-2.5">
            <SignerAvatar signer="planner" size={34} />
            <p
              className="min-w-0 flex-1 rounded-2xl rounded-tl-md border-2 border-planner/30 bg-planner-light px-4 py-3 text-sm font-bold leading-relaxed text-ink wrap-anywhere"
              data-testid="summary-text"
            >
              {item.summary_text}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(SIGNER_LABELS) as (keyof typeof SIGNER_LABELS)[]).map((signer) => (
              <span key={signer} className="inline-flex items-center gap-1.5 rounded-full border-2 border-border bg-surface px-2 py-0.5 text-xs font-extrabold">
                <SignerAvatar signer={signer} size={18} />
                {SIGNER_LABELS[signer]} <VerdictBadge verdict={item.verdicts[signer].verdict} />
              </span>
            ))}
          </div>
        </section>
        <section aria-label="Fields you sign" className="space-y-3">
          <h4 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-muted">
            <ReceiptText className="h-4 w-4" aria-hidden />
            What you sign (decoded from the typed data)
          </h4>
          {decoded.payout ? (
            <dl
              className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 rounded-2xl border-2 border-dashed border-border-strong bg-surface-2 p-4 text-sm"
              data-testid="decoded-fields"
            >
              {decoded.payout.rows.map((row) => (
                <div key={row.field} className="contents">
                  <dt className="font-bold text-muted">{row.label}</dt>
                  <dd className="hash text-ink" data-testid={`field-${row.field}`}>
                    {row.value}
                  </dd>
                </div>
              ))}
              <dt className="font-bold text-muted">Chain</dt>
              <dd className="hash text-ink">{String(item.typed_data.domain.chainId)}</dd>
              <dt className="font-bold text-muted">Vault</dt>
              <dd className="hash text-ink">{item.typed_data.domain.verifyingContract}</dd>
            </dl>
          ) : (
            <ErrorNote error={`The typed data cannot be decoded: ${decoded.error}`} />
          )}
        </section>
        <section className="lg:col-span-2" aria-label="Checks">
          {safe ? (
            <div className="flex items-center gap-3 rounded-2xl border-2 border-primary/40 bg-primary-light px-4 py-3" data-testid="checks-ok">
              <Kancil pose="happy" prop="shield" size={52} title="Kancil, satisfied" />
              <p className="text-sm font-extrabold text-success">
                The summary matches the signed fields, and the domain names this vault on chain {config.chainId}.
              </p>
            </div>
          ) : (
            <div role="alert" data-testid="checks-failed" className="flex items-start gap-3 rounded-2xl border-2 border-danger/30 bg-danger-light px-4 py-3 text-sm text-danger">
              <Kancil pose="alert" size={52} title="Kancil, on alert" />
              <div>
                <p className="font-extrabold">Do not sign. What you would sign does not match.</p>
                <ul className="mt-1 list-disc pl-5 font-bold">
                  {[...domainCheck.problems, ...summaryCheck.problems].map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
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
