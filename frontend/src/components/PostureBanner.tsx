import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import { api, mockControls } from "@/api";
import { Button } from "@/components/ui/button";
import { shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

/** Shown on every page while the vault's security posture is above 0 (task D4). */
export function PostureBanner() {
  const { identity } = useIdentity();
  const posture = useQuery({
    queryKey: ["posture", identity.role],
    queryFn: () => api.posture(identity),
    refetchInterval: 30_000,
  });
  const level = posture.data?.level ?? 0;
  const controls = mockControls;

  return (
    <>
      {level > 0 && (
        <div role="status" data-testid="posture-banner" className="border-b border-warning/40 bg-warning/10">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-2 text-sm text-warning">
            <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden />
            <span>
              Security posture is raised to level {level}. Every payout needs a trustee signature until two trustees lower it.
            </span>
            {posture.data?.last_report_hash && (
              <span className="hash text-xs opacity-80">Report {shortHex(posture.data.last_report_hash)}</span>
            )}
          </div>
        </div>
      )}
      {controls && (
        <MockPostureControl
          level={level}
          onChange={(next) => {
            controls.setPosture(next);
            void posture.refetch();
          }}
        />
      )}
    </>
  );
}

function MockPostureControl({ level, onChange }: { level: number; onChange: (level: number) => void }) {
  return (
    <div className="mx-auto flex max-w-6xl justify-end px-4 pt-2">
      <Button variant="ghost" size="sm" onClick={() => onChange(level > 0 ? 0 : 1)} data-testid="mock-posture-toggle">
        {level > 0 ? "Lower posture (mock)" : "Raise posture (mock)"}
      </Button>
    </div>
  );
}
