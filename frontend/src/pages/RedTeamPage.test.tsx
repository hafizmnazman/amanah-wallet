import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { facts } from "@/lib/facts";

import { amanahBound, RedTeamPage, soundAndRepeats, type LegitFacts, type ReproFacts, type SeedFacts } from "./RedTeamPage";

type Arm = { n: number; successes: number; upper95: number; seeds_with_a_success: number };
type Pooled = { n: number; n_transfer: number; arms: Record<string, Arm> };
const variants = (
  facts as unknown as { variants?: { population: number; pooled: Pooled; seeds?: SeedFacts; legit?: LegitFacts; repro?: ReproFacts } }
).variants;

describe("the Red Team page", () => {
  it.runIf(variants)("renders the random variants with their counts from facts.json", () => {
    const html = renderToStaticMarkup(<RedTeamPage />);
    const section = /<section[^>]*data-testid="random-variants"[^>]*>(.*?)<\/section>/s.exec(html)?.[1] ?? "";
    const { pooled, population } = variants!;
    expect(section).toContain(`Then ${pooled.n} More, Drawn at Random`);
    expect(section).toContain(population.toLocaleString());
    expect(section).toContain(`${pooled.arms.S1.successes}/${pooled.arms.S1.n}`);
    expect(section).toContain(`${pooled.arms.S5.successes}/${pooled.arms.S5.n}`);
  });

  it.runIf(variants?.legit && variants?.repro)("adds one line on the sound payouts and the repeats, from facts.json", () => {
    const html = renderToStaticMarkup(<RedTeamPage />);
    const line = /<p[^>]*data-testid="variants-sound"[^>]*>(.*?)<\/p>/s.exec(html)?.[1];
    const { legit, repro } = variants!;
    expect(line).toBe(soundAndRepeats(legit!, repro!));
    // The committed runs: 14 of 60 sound payouts held for a person, 26 of 30 planner repeats, none through Amanah
    expect(legit!.arms.S5.held).toBe(14);
    expect(line).toBe(
      "Sound payouts too: of 60, the auditor stopped 14 (all flood-relief grants, no recorded request matched the amount) " +
        "for a person to check; nothing sound was refused outright. The ten planner failures repeated in 26 of 30 fresh runs; " +
        "Amanah moved nothing in any.",
    );
  });

  it.runIf(variants?.seeds)("labels the bound as counted per variant, with the per-seed bound beside it", () => {
    const html = renderToStaticMarkup(<RedTeamPage />);
    const bound = /<p[^>]*data-testid="variants-bound"[^>]*>(.*?)<\/p>/s.exec(html)?.[1];
    expect(bound).toBe(amanahBound(variants!.pooled, variants!.seeds));
    expect(bound).toBe(
      "Under 1.1% at 95% confidence, counted per variant; the 300 reword the 44 seed ideas, and per seed none of 40 moved (under 7.2%).",
    );
  });

  it("gives only the labelled per-variant bound when the facts have no seed count", () => {
    const pooled: Pooled = { n: 300, n_transfer: 272, arms: { S5: { n: 272, successes: 0, upper95: 0.01095, seeds_with_a_success: 0 } } };
    expect(amanahBound(pooled)).toBe("Under 1.1% at 95% confidence, counted per variant.");
    expect(amanahBound(pooled, { ideas: 44, transfer: 40, moved: 2, upper95: 0.15 })).toContain("per seed 2 of 40 moved (under 15.0%)");
  });

  it("claims the auditor, the ground and no outright refusal only when the facts carry them", () => {
    const legit: LegitFacts = { n: 60, arms: { S5: { held: 15, n: 60 } }, through_vault: 44, reason: null };
    const repro: ReproFacts = { cases: 14, repeats: 3, arms: { S1: { successes: 30, n: 42 }, S5: { successes: 1, n: 42 } } };
    expect(soundAndRepeats(legit, repro)).toBe(
      "Sound payouts too: of 60, the checks held 15 for a person to check. The 14 planner failures repeated in 30 of 42 fresh runs; " +
        "Amanah moved funds in 1.",
    );
  });

  it("lists every attack of the final run", () => {
    const rows = renderToStaticMarkup(<RedTeamPage />).match(/data-testid="redteam-row"/g) ?? [];
    expect(rows).toHaveLength(facts.redteam.cases.filter((c) => c.attack).length);
  });
});
