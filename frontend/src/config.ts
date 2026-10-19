/** Runtime settings from VITE_ variables; see .env.example. */
const env = import.meta.env;

function flag(value: string | undefined): boolean {
  return value === "1" || value === "true";
}

export const config = {
  apiUrl: (env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, ""),
  mock: flag(env.VITE_MOCK_API),
  mockLatencyMs: Number(env.VITE_MOCK_LATENCY_MS ?? 200),
  chainId: Number(env.VITE_CHAIN_ID || 84532),
  vaultAddress: env.VITE_VAULT_ADDRESS || "",
  rpcUrl: env.VITE_RPC_URL || undefined,
  explorerUrl: (env.VITE_EXPLORER_URL || "https://base-sepolia.blockscout.com").replace(/\/$/, ""),
  devSigning: flag(env.VITE_DEV_SIGNING),
  devTrusteeKey: (env.VITE_DEV_TRUSTEE_KEY || undefined) as `0x${string}` | undefined,
} as const;
