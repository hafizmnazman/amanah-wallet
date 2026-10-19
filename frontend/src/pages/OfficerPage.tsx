import { ChatPanel } from "@/components/chat/ChatPanel";
import { RoleHint } from "@/components/common";
import { ScheduledDrafts } from "@/components/plan/ScheduledDrafts";
import { useIdentity } from "@/session/IdentityContext";

export function OfficerPage() {
  const { identity } = useIdentity();
  return (
    <div className="space-y-4">
      <RoleHint expected={identity.role === "finance_officer"} label="finance officers" role="finance_officer" />
      <ScheduledDrafts />
      <ChatPanel />
    </div>
  );
}
