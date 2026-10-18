import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Layout } from "@/components/Layout";
import { OfficerPage } from "@/pages/OfficerPage";
import { ProofPage } from "@/pages/ProofPage";
import { QueuePage } from "@/pages/QueuePage";
import { TrusteePage } from "@/pages/TrusteePage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/officer" replace />} />
          <Route path="officer" element={<OfficerPage />} />
          <Route path="trustee" element={<TrusteePage />} />
          <Route path="queue" element={<QueuePage />} />
          <Route path="proof" element={<ProofPage />} />
          <Route path="*" element={<Navigate to="/officer" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
