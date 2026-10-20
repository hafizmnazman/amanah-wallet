import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Layout } from "@/components/Layout";
import { BrandPage } from "@/pages/BrandPage";
import { HomePage } from "@/pages/HomePage";
import { OfficerPage } from "@/pages/OfficerPage";
import { ProofPage } from "@/pages/ProofPage";
import { QueuePage } from "@/pages/QueuePage";
import { RedTeamPage } from "@/pages/RedTeamPage";
import { TrusteePage } from "@/pages/TrusteePage";
import { UsagePage } from "@/pages/UsagePage";

export function App() {
  return (
    // The base is "/" except for the GitHub Pages mirror, which serves the demo under /amanah-wallet/
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="officer" element={<OfficerPage />} />
          <Route path="trustee" element={<TrusteePage />} />
          <Route path="redteam" element={<RedTeamPage />} />
          <Route path="queue" element={<QueuePage />} />
          <Route path="proof" element={<ProofPage />} />
          <Route path="usage" element={<UsagePage />} />
          <Route path="brand" element={<BrandPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
