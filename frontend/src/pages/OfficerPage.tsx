import { ChatPanel } from "@/components/chat/ChatPanel";
import { RoleHint } from "@/components/common";
import { useIdentity } from "@/session/IdentityContext";

export function OfficerPage() {
  const { identity } = useIdentity();
  return (
    <div className="space-y-4">
      <RoleHint expected={identity.role === "finance_officer"} label="finance officers" />
      <ChatPanel />
    </div>
  );
}
