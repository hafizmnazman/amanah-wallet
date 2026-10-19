import { StatusBadge } from "@/components/common";
import { Kancil, type KancilPose, type KancilProp } from "@/components/mascot/Kancil";
import { SIGNER_ORDER, SignerChip } from "@/components/signers";
import { Button } from "@/components/ui/button";

const POSES: { pose: KancilPose; prop: KancilProp; when: string }[] = [
  { pose: "wave", prop: "key", when: "Hello, on the home page" },
  { pose: "happy", prop: null, when: "A payout is paid" },
  { pose: "alert", prop: null, when: "A trick is spotted, or the posture rises" },
  { pose: "thinking", prop: null, when: "The checks are running" },
  { pose: "happy", prop: "shield", when: "Every check passed" },
  { pose: "sleep", prop: null, when: "Nothing is waiting" },
];

const SWATCHES = [
  { name: "Bank Blue", hex: "#1d4ed8", use: "Actions and the vault" },
  { name: "Navy", hex: "#0b1f4b", use: "Structure and text" },
  { name: "Gold", hex: "#d8a521", use: "Trust, the key, trustees" },
  { name: "Kancil Blue", hex: "#4f7fe8", use: "The guide" },
  { name: "Terracotta", hex: "#d9643a", use: "Planner, Claude" },
  { name: "Violet", hex: "#7a5af0", use: "Auditor, Qwen" },
  { name: "Teal", hex: "#0f9aa8", use: "Sentinel, rules" },
  { name: "Red", hex: "#e5484d", use: "Refusals" },
];

/** The design system: Sang Kancil, the palette, type and components. The deck's design slide is taken from here. */
export function BrandPage() {
  return (
    <div className="space-y-10" data-testid="brand-page">
      <section className="space-y-2">
        <h1 className="text-3xl font-black">Design System</h1>
        <p className="max-w-2xl text-muted">
          Friendly on the surface, strict underneath: a bank's blue, navy and gold, chunky shapes, and one colour
          per signer, so the quorum reads at a glance. Sang Kancil speaks in short, warm sentences and never jokes about
          money.
        </p>
      </section>

      <section className="space-y-3" data-testid="brand-poses">
        <h2 className="text-xl font-black">Sang Kancil, the Guide</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {POSES.map((p) => (
            <figure key={`${p.pose}-${p.prop}`} className="chunky flex flex-col items-center gap-2 p-4 text-center">
              <Kancil pose={p.pose} prop={p.prop} size={110} />
              <figcaption className="text-xs font-bold text-muted">{p.when}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="space-y-3" data-testid="brand-colours">
        <h2 className="text-xl font-black">Colour</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {SWATCHES.map((s) => (
            <div key={s.name} className="chunky overflow-hidden">
              <div className="h-16" style={{ background: s.hex }} />
              <div className="p-3">
                <p className="font-black">{s.name}</p>
                <p className="hash text-xs text-muted">{s.hex}</p>
                <p className="text-xs font-bold text-ink/80">{s.use}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="chunky space-y-2 p-5" data-testid="brand-type">
          <h2 className="text-xl font-black">Type: Plus Jakarta Sans and Inter</h2>
          <p className="font-display text-4xl font-extrabold">Heading, Jakarta 800</p>
          <p className="font-display text-2xl font-bold">Subheading, Jakarta 700</p>
          <p className="text-base font-medium">Body text, Inter 500: short sentences, plain words.</p>
          <p className="hash text-sm text-muted">0x558e8E8b...4FC5, hashes in mono</p>
        </div>
        <div className="chunky space-y-4 p-5" data-testid="brand-components">
          <h2 className="text-xl font-black">Components</h2>
          <div className="flex flex-wrap gap-2">
            <Button>Confirm</Button>
            <Button variant="secondary">Start Over</Button>
            <Button variant="sky">Sign</Button>
            <Button variant="destructive">Refuse</Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {SIGNER_ORDER.map((s) => (
              <SignerChip key={s} signer={s} verdict="APPROVE" signed />
            ))}
            <SignerChip signer="auditor" verdict="REJECT" signed={false} />
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="paid" />
            <StatusBadge status="elevated_pending" />
            <StatusBadge status="rejected" />
            <StatusBadge status="queued" />
          </div>
        </div>
      </section>
    </div>
  );
}
