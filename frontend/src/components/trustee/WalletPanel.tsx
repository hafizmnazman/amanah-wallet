import { Wallet } from "lucide-react";
import { useAccount, useConnect, useDisconnect, useSwitchChain } from "wagmi";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { config } from "@/config";
import { shortHex } from "@/lib/utils";
import { SUPPORTED_CHAINS } from "@/wallet/wagmi";

/** MetaMask connection for trustees, through the injected connector. */
export function WalletPanel() {
  const account = useAccount();
  const { connect, connectors, isPending, error } = useConnect();
  const { disconnect } = useDisconnect();
  const { switchChain, isPending: switching } = useSwitchChain();
  const injected = connectors[0];
  const wrongChain = account.isConnected && account.chainId !== config.chainId;

  return (
    <div className="chunky flex flex-wrap items-center gap-3 p-4 text-sm" data-testid="wallet-panel">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border-2 border-sky/40 bg-sky-light text-sky-dark">
        <Wallet className="h-5 w-5" aria-hidden />
      </span>
      {account.isConnected ? (
        <>
          <span className="hash font-bold">{shortHex(account.address ?? "")}</span>
          <Badge variant={wrongChain ? "warning" : "teal"}>
            {SUPPORTED_CHAINS[account.chainId ?? 0] ?? `Chain ${account.chainId}`}
          </Badge>
          {wrongChain && (
            <Button size="sm" variant="secondary" disabled={switching} onClick={() => switchChain({ chainId: config.chainId })}>
              Switch to {SUPPORTED_CHAINS[config.chainId] ?? `chain ${config.chainId}`}
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => disconnect()}>
            Disconnect
          </Button>
        </>
      ) : (
        <>
          <span className="font-bold text-muted">Connect the trustee wallet to sign in MetaMask.</span>
          <Button size="sm" variant="sky" disabled={!injected || isPending} onClick={() => injected && connect({ connector: injected })}>
            {injected ? "Connect MetaMask" : "No browser wallet found"}
          </Button>
        </>
      )}
      {error && <span className="w-full font-bold text-danger">{error.message}</span>}
    </div>
  );
}
