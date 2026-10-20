/**
 * The hash-chained action log (plan section 3.5), checked in the browser exactly as the backend checks it
 * (backend/app/agentwallet/evidence.py, ActionLog.verify): each record's hash is the SHA-256 of the record
 * without its hash, in canonical JSON, and each prev_hash is the hash of the record before, from 64 zeros.
 */
export const GENESIS = "0".repeat(64);

export interface ActionLogEntry {
  seq: number;
  ts: string;
  actor: string;
  lineage: string;
  event: string;
  status?: string;
  prev_hash: string;
  hash: string;
  [field: string]: unknown;
}

export interface ChainCheck {
  ok: boolean;
  /** Records whose link and hash both checked out, counted up to the first break. */
  verified: number;
  total: number;
  /** The last verified hash: the head, when the whole chain holds. */
  head: string;
  /** Where it broke: the record's seq (its line when seq is missing), and why. */
  brokenAt?: number;
  problem?: string;
}

export function parseActionLog(text: string): ActionLogEntry[] {
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as ActionLogEntry);
}

/**
 * Python's json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False). Keys sort by code point
 * and strings escape as JSON.stringify does. The log holds strings and integers only; a float would need
 * Python's repr, which this does not attempt.
 */
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record)
      .filter((k) => record[k] !== undefined)
      .sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonical(record[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function verifyActionLog(entries: ActionLogEntry[]): Promise<ChainCheck> {
  let prev = GENESIS;
  let verified = 0;
  for (const [i, entry] of entries.entries()) {
    const { hash: stated, ...record } = entry;
    const at = typeof entry.seq === "number" ? entry.seq : i + 1;
    const broken = (problem: string): ChainCheck => ({ ok: false, verified, total: entries.length, head: prev, brokenAt: at, problem });
    if (record.prev_hash !== prev) return broken("its prev_hash does not match the record before");
    if (record.seq !== i + 1) return broken(`seq ${String(record.seq)} where ${i + 1} was expected`);
    if ((await sha256Hex(canonical(record))) !== stated) return broken("its hash does not match its contents");
    prev = stated;
    verified += 1;
  }
  return { ok: true, verified, total: entries.length, head: prev };
}

const CSV_COLUMNS = ["seq", "ts", "actor", "event", "status", "lineage", "prev_hash", "hash"] as const;

function csvCell(value: unknown): string {
  const text = value === undefined || value === null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function actionLogCsv(entries: ActionLogEntry[]): string {
  const rows = entries.map((entry) => CSV_COLUMNS.map((column) => csvCell(entry[column])).join(","));
  return `${[CSV_COLUMNS.join(","), ...rows].join("\r\n")}\r\n`;
}
