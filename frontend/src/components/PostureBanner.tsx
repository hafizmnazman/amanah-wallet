import { useQuery } from "@tanstack/react-query";

import { api, mockControls } from "@/api";
import { Kancil } from "@/components/mascot/Kancil";
import { Button } from "@/components/ui/button";
import { shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

/** Shown on every page while the vault's security posture is above 0 (task D4). Kancil is on alert. */
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
        <div role="status" data-testid="posture-banner" className="border-b-2 border-gold/40 bg-gold-light">
          <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5 lg:px-8">
            <Kancil pose="alert" size={42} title="Kancil on alert" />
            <div className="min-w-0 text-sm">
              <p className="font-extrabold text-warning">
                Security posture is raised to level {level}. Every payout needs a trustee signature until two trustees lower it.
              </p>
              {posture.data?.last_report_hash && (
                <p className="hash text-xs text-warning/80">Red-team report {shortHex(posture.data.last_report_hash)}</p>
              )}
            </div>
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
    <div className="mx-auto flex max-w-5xl justify-end px-4 pt-2 lg:px-8">
      <Button variant="ghost" size="sm" onClick={() => onChange(level > 0 ? 0 : 1)} data-testid="mock-posture-toggle">
        {level > 0 ? "Lower posture (mock)" : "Raise posture (mock)"}
      </Button>
    </div>
  );
}
