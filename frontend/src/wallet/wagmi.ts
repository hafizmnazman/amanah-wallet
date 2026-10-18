import { createConfig, http } from "wagmi";
import { anvil, baseSepolia } from "wagmi/chains";
import { injected } from "wagmi/connectors";

import { config } from "@/config";

/** Trustees sign in MetaMask through the injected connector, on Base Sepolia or a local Anvil. */
export const wagmiConfig = createConfig({
  chains: [baseSepolia, anvil],
  connectors: [injected()],
  transports: {
    [baseSepolia.id]: http(config.rpcUrl),
    [anvil.id]: http("http://127.0.0.1:8545"),
  },
});

export const SUPPORTED_CHAINS = { [baseSepolia.id]: "Base Sepolia", [anvil.id]: "Anvil" } as Record<number, string>;
