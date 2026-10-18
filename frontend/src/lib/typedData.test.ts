import { hashTypedData } from "viem";
import { describe, expect, it } from "vitest";

import type { EIP712TypedData } from "@/api/types";

import { PAYOUT_TYPE } from "./eip712";
import { checkSummary } from "./summaryCheck";
import { checkTypedData, decodePayout, toSignable } from "./typedData";

const VAULT = "0xa3A1000000000000000000000000000000000001";

function typedData(overrides: Partial<EIP712TypedData> = {}): EIP712TypedData {
  return {
    domain: { name: "AmanahVault", version: "1", chainId: 84532, verifyingContract: VAULT },
    types: { Payout: PAYOUT_TYPE.map((f) => ({ ...f })) },
    primaryType: "Payout",
    message: {
      proposalId: `0x${"11".repeat(32)}`,
      programmeId: `0x${"22".repeat(32)}`,
      beneficiary: "0x83febFBb2d0ebDBb7BA11F7A10e84c39D88DA29a",
      amount: "1200000000",
      evidenceHash: `0x${"33".repeat(32)}`,
      nonce: "42",
      deadline: "1792300000",
    },
    ...overrides,
  };
}

describe("decodePayout", () => {
  it("decodes every field from the typed data", () => {
    const p = decodePayout(typedData());
    expect(p.amount).toBe(1_200_000_000n);
    expect(p.nonce).toBe(42n);
    expect(p.rows.map((r) => r.field)).toEqual(PAYOUT_TYPE.map((f) => f.name));
    expect(p.rows.find((r) => r.field === "amount")?.value).toBe("1,200.00 USDC (1200000000 base units)");
    expect(p.rows.find((r) => r.field === "deadline")?.value).toBe("2026-10-18 05:06 UTC");
  });

  it("refuses malformed fields", () => {
    const bad = typedData();
    bad.message.amount = "-5";
    expect(() => decodePayout(bad)).toThrow(/amount/);
    const badHex = typedData();
    badHex.message.beneficiary = "not an address";
    expect(() => decodePayout(badHex)).toThrow(/beneficiary/);
  });
});

describe("checkTypedData", () => {
  const expected = { chainId: 84532, vaultAddress: VAULT };

  it("passes a payout for this vault on this chain", () => {
    expect(checkTypedData(typedData(), expected)).toEqual({ ok: true, problems: [] });
  });

  it("compares the vault address without regard to case", () => {
    expect(checkTypedData(typedData(), { ...expected, vaultAddress: VAULT.toLowerCase() }).ok).toBe(true);
  });

  it("flags another chain, another contract and a missing expected vault", () => {
    const otherChain = typedData({ domain: { name: "AmanahVault", version: "1", chainId: 1, verifyingContract: VAULT } });
    expect(checkTypedData(otherChain, expected).problems).toEqual(["Chain is 1, but this app is set to 84532."]);
    const otherVault = typedData({
      domain: { name: "AmanahVault", version: "1", chainId: 84532, verifyingContract: `0x${"de".repeat(20)}` },
    });
    expect(checkTypedData(otherVault, expected).problems[0]).toMatch(/Contract is 0xdede/);
    expect(checkTypedData(typedData(), { ...expected, vaultAddress: "" }).problems).toEqual([
      "VITE_VAULT_ADDRESS is not set, so the contract cannot be checked.",
    ]);
  });

  it("flags a renamed domain and a changed Payout type", () => {
    const renamed = typedData({ domain: { name: "Other", version: "2", chainId: 84532, verifyingContract: VAULT } });
    expect(checkTypedData(renamed, expected).problems).toHaveLength(2);
    const reordered = typedData();
    reordered.types.Payout = [...reordered.types.Payout].reverse();
    expect(checkTypedData(reordered, expected).problems).toEqual(["The Payout type differs from shared/eip712.json."]);
  });
});

describe("toSignable", () => {
  it("gives viem the same digest as the vault's hashPayout vector", async () => {
    // shared/vectors.json, written by contracts/test/Vectors.t.sol
    const vectors = (await import("../../../shared/vectors.json")).default;
    const m = vectors.payout.message;
    const td = typedData({
      domain: { ...vectors.domain },
      message: { ...m },
    });
    expect(hashTypedData(toSignable(td))).toBe(vectors.payout.digest);
  });
});

describe("checkSummary", () => {
  const payout = decodePayout(typedData());

  it("passes a summary that names the signed amount and wallet", () => {
    const summary =
      "Pay 1,200.00 USDC to household REL-H-03. It is above the 300.00 USDC cap. " +
      "Beneficiary wallet 0x83febFBb2d0ebDBb7BA11F7A10e84c39D88DA29a.";
    expect(checkSummary(summary, payout)).toEqual({ ok: true, problems: [] });
  });

  it("flags a summary whose amount or wallet differs from what is signed", () => {
    expect(checkSummary("Pay 120.00 USDC to household REL-H-03.", payout).problems[0]).toMatch(/signed amount is 1,200.00/);
    expect(checkSummary(`Pay 1,200.00 USDC to 0x${"ab".repeat(20)}.`, payout).problems[0]).toMatch(/signed beneficiary/);
    expect(checkSummary("Pay household REL-H-03.", payout).problems).toEqual(["The summary names no amount."]);
  });
});
