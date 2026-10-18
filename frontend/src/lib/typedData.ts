import type { EIP712TypedData } from "@/api/types";

import { DOMAIN_NAME, DOMAIN_VERSION, PAYOUT_TYPE } from "./eip712";
import { formatBaseUnits } from "./usdc";

/** A payout as the trustee's wallet will show it, decoded from the typed data and nothing else. */
export interface DecodedPayout {
  proposalId: `0x${string}`;
  programmeId: `0x${string}`;
  beneficiary: `0x${string}`;
  amount: bigint;
  evidenceHash: `0x${string}`;
  nonce: bigint;
  deadline: bigint;
  /** Label and display value per field, in the order the wallet lists them. */
  rows: { field: string; label: string; value: string }[];
}

const LABELS: Record<string, string> = {
  proposalId: "Proposal",
  programmeId: "Programme (opaque id)",
  beneficiary: "Beneficiary wallet",
  amount: "Amount",
  evidenceHash: "Evidence hash",
  nonce: "Nonce",
  deadline: "Signature valid until",
};

function hex(value: unknown, field: string): `0x${string}` {
  if (typeof value !== "string" || !/^0x[0-9a-fA-F]*$/.test(value)) {
    throw new Error(`${field} is not a hex string`);
  }
  return value as `0x${string}`;
}

function uint(value: unknown, field: string): bigint {
  if (typeof value === "bigint") return value;
  if ((typeof value === "string" && /^\d+$/.test(value)) || (typeof value === "number" && Number.isSafeInteger(value))) {
    return BigInt(value);
  }
  throw new Error(`${field} is not an unsigned integer`);
}

export function formatDeadline(deadline: bigint): string {
  const date = new Date(Number(deadline) * 1000);
  return `${date.toISOString().replace("T", " ").slice(0, 16)} UTC`;
}

/** Decodes a Payout message. Throws when a field is missing or malformed. */
export function decodePayout(typedData: EIP712TypedData): DecodedPayout {
  const m = typedData.message;
  const decoded = {
    proposalId: hex(m.proposalId, "proposalId"),
    programmeId: hex(m.programmeId, "programmeId"),
    beneficiary: hex(m.beneficiary, "beneficiary"),
    amount: uint(m.amount, "amount"),
    evidenceHash: hex(m.evidenceHash, "evidenceHash"),
    nonce: uint(m.nonce, "nonce"),
    deadline: uint(m.deadline, "deadline"),
  };
  const display: Record<string, string> = {
    proposalId: decoded.proposalId,
    programmeId: decoded.programmeId,
    beneficiary: decoded.beneficiary,
    amount: `${formatBaseUnits(decoded.amount)} USDC (${decoded.amount.toString()} base units)`,
    evidenceHash: decoded.evidenceHash,
    nonce: decoded.nonce.toString(),
    deadline: formatDeadline(decoded.deadline),
  };
  return {
    ...decoded,
    rows: PAYOUT_TYPE.map(({ name }) => ({ field: name, label: LABELS[name] ?? name, value: display[name] })),
  };
}

export interface DomainCheck {
  ok: boolean;
  problems: string[];
}

/**
 * Checks what a trustee is about to sign against this deployment: the vault's name and version,
 * the chain, the contract, and the Payout type itself. Any problem means do not sign.
 */
export function checkTypedData(
  typedData: EIP712TypedData,
  expected: { chainId: number; vaultAddress: string },
): DomainCheck {
  const problems: string[] = [];
  const d = typedData.domain;
  if (d.name !== DOMAIN_NAME) problems.push(`Domain name is "${d.name}", expected "${DOMAIN_NAME}".`);
  if (d.version !== DOMAIN_VERSION) problems.push(`Domain version is "${d.version}", expected "${DOMAIN_VERSION}".`);
  if (Number(d.chainId) !== expected.chainId) {
    problems.push(`Chain is ${d.chainId}, but this app is set to ${expected.chainId}.`);
  }
  if (!expected.vaultAddress) {
    problems.push("VITE_VAULT_ADDRESS is not set, so the contract cannot be checked.");
  } else if (String(d.verifyingContract).toLowerCase() !== expected.vaultAddress.toLowerCase()) {
    problems.push(`Contract is ${d.verifyingContract}, but the vault is ${expected.vaultAddress}.`);
  }
  if (typedData.primaryType !== "Payout") problems.push(`Primary type is "${typedData.primaryType}", expected "Payout".`);
  const fields = typedData.types.Payout ?? [];
  const same =
    fields.length === PAYOUT_TYPE.length &&
    fields.every((f, i) => f.name === PAYOUT_TYPE[i].name && f.type === PAYOUT_TYPE[i].type);
  if (!same) problems.push("The Payout type differs from shared/eip712.json.");
  return { ok: problems.length === 0, problems };
}

/** The arguments viem and wagmi's signTypedData take, with the domain type left out as they expect. */
export function toSignable(typedData: EIP712TypedData) {
  const p = decodePayout(typedData);
  return {
    domain: {
      name: typedData.domain.name,
      version: typedData.domain.version,
      chainId: Number(typedData.domain.chainId),
      verifyingContract: hex(typedData.domain.verifyingContract, "verifyingContract"),
    },
    types: { Payout: PAYOUT_TYPE.map((f) => ({ ...f })) },
    primaryType: "Payout" as const,
    message: {
      proposalId: p.proposalId,
      programmeId: p.programmeId,
      beneficiary: p.beneficiary,
      amount: p.amount,
      evidenceHash: p.evidenceHash,
      nonce: p.nonce,
      deadline: p.deadline,
    },
  };
}
