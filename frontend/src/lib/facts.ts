import data from "@/data/facts.json";

/**
 * Measured facts for the home and red-team pages, written by scripts/export_ui_data.py from the committed
 * run files. The app never states one of these numbers by hand.
 */
export const facts = data;

export type Rate = { k: number; n: number; rate: number; ci: number[] };
export type RedTeamCase = (typeof data.redteam.cases)[number];

export const ARMS = ["S1", "S2", "S3", "S4", "S5"] as const;
export type Arm = (typeof ARMS)[number];

export const ARM_LABELS: Record<Arm, { short: string; long: string }> = {
  S1: { short: "Planner Alone", long: "One model holds the key: a typical agent wallet" },
  S2: { short: "+ Claude Auditor", long: "The planner and a second model of the same family" },
  S3: { short: "+ Qwen Auditor", long: "The planner and an auditor of another lineage, which sees only a case file" },
  S4: { short: "+ Sentinel", long: "S3 and the rules on numbers" },
  S5: { short: "+ Vault", long: "S4 and the contract, on a local chain" },
};

export const BLOCKSCOUT = facts.base_sepolia.explorer;
export const VAULT_URL = `${BLOCKSCOUT}/address/${facts.base_sepolia.vault}`;
export const REPO_URL = "https://github.com/hafizmnazman/amanah-wallet";
export const REPORT_URL = `${REPO_URL}/blob/main/redteam/results/final/report.md`;

export function rateOf(r: unknown): Rate | null {
  return r && typeof r === "object" && "k" in r ? (r as Rate) : null;
}

export function usd(n: number): string {
  return n.toLocaleString("en-US");
}
