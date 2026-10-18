/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_MOCK_API?: string;
  readonly VITE_MOCK_LATENCY_MS?: string;
  readonly VITE_CHAIN_ID?: string;
  readonly VITE_VAULT_ADDRESS?: string;
  readonly VITE_RPC_URL?: string;
  readonly VITE_EXPLORER_URL?: string;
  readonly VITE_DEV_SIGNING?: string;
  readonly VITE_DEV_TRUSTEE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
