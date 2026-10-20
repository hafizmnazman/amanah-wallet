import { describe, expect, it } from "vitest";

import raw from "@/data/action-log.jsonl?raw";

import { actionLogCsv, canonical, GENESIS, parseActionLog, sha256Hex, verifyActionLog, type ActionLogEntry } from "./actionLog";

// evidence/demo-summary.json: the head the 19 October run anchored on Base Sepolia
const ANCHORED_HEAD = "487218f0aba40a763bef66a8275480f6ada1990bfe1ce6d6a85a797a2a9ec212";

const copy = (entries: ActionLogEntry[]) => entries.map((e) => ({ ...e }));

describe("the action log, checked in the browser", () => {
  const entries = parseActionLog(raw);

  it("writes canonical JSON as Python's json.dumps(sort_keys=True, separators=(',', ':')) does", async () => {
    expect(canonical({ b: 1, a: "x", c: { z: true, y: null }, d: ["é", 2] })).toBe('{"a":"x","b":1,"c":{"y":null,"z":true},"d":["é",2]}');
    // hashlib.sha256(b"abc").hexdigest()
    expect(await sha256Hex("abc")).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });

  it("verifies all 88 links of the 19 October Base Sepolia run, ending at the anchored head", async () => {
    expect(entries).toHaveLength(88);
    expect(entries[0].prev_hash).toBe(GENESIS);
    const check = await verifyActionLog(entries);
    expect(check).toMatchObject({ ok: true, verified: 88, total: 88, head: ANCHORED_HEAD });
    expect(entries[87].hash).toBe(ANCHORED_HEAD);
  });

  it("breaks at the edited record when one is changed", async () => {
    const tampered = copy(entries);
    tampered[39] = { ...tampered[39], status: `${tampered[39].status ?? ""} (edited)` };
    const check = await verifyActionLog(tampered);
    expect(check).toMatchObject({ ok: false, verified: 39, brokenAt: 40, problem: "its hash does not match its contents" });
  });

  it("breaks at the next record when the edit is re-hashed to hide it", async () => {
    const tampered = copy(entries);
    const { hash: _old, ...edited } = { ...tampered[39], actor: "someone else" };
    tampered[39] = { ...edited, hash: await sha256Hex(canonical(edited)) } as ActionLogEntry;
    const check = await verifyActionLog(tampered);
    expect(check).toMatchObject({ ok: false, verified: 40, brokenAt: 41, problem: "its prev_hash does not match the record before" });
  });

  it("notices a dropped record by its sequence number", async () => {
    const dropped = copy(entries).filter((e) => e.seq !== 1);
    expect((await verifyActionLog(dropped)).brokenAt).toBe(2);
  });

  it("exports a CSV with the proof page's columns, one row per record", () => {
    const lines = actionLogCsv(entries).trimEnd().split("\r\n");
    expect(lines[0]).toBe("seq,ts,actor,event,status,lineage,prev_hash,hash");
    expect(lines).toHaveLength(89);
    expect(lines[1]).toBe(
      ["1", entries[0].ts, "demo", "scenario", "1: pass", "human", GENESIS, entries[0].hash].join(","),
    );
    expect(actionLogCsv([{ ...entries[0], status: 'a, "b"' }]).split("\r\n")[1]).toContain('"a, ""b"""');
  });
});
