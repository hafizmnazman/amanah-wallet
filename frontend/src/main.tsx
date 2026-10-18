import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { WagmiProvider } from "wagmi";

import { App } from "@/App";
import { FundProvider } from "@/session/FundContext";
import { IdentityProvider } from "@/session/IdentityContext";
import { wagmiConfig } from "@/wallet/wagmi";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <IdentityProvider>
          <FundProvider>
            <App />
          </FundProvider>
        </IdentityProvider>
      </QueryClientProvider>
    </WagmiProvider>
  </StrictMode>,
);
