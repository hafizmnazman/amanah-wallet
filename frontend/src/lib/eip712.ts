/**
 * The EIP-712 types from shared/eip712.json, copied here so the app stands alone.
 * src/lib/eip712.test.ts fails if this copy drifts from the shared file.
 */
export interface TypedField {
  name: string;
  type: string;
}

export const DOMAIN_NAME = "AmanahVault";
export const DOMAIN_VERSION = "1";

export const PAYOUT_TYPE: readonly TypedField[] = [
  { name: "proposalId", type: "bytes32" },
  { name: "programmeId", type: "bytes32" },
  { name: "beneficiary", type: "address" },
  { name: "amount", type: "uint256" },
  { name: "evidenceHash", type: "bytes32" },
  { name: "nonce", type: "uint256" },
  { name: "deadline", type: "uint256" },
];

export const GOVERNANCE_TYPE: readonly TypedField[] = [
  { name: "action", type: "bytes32" },
  { name: "paramsHash", type: "bytes32" },
  { name: "govNonce", type: "uint256" },
  { name: "deadline", type: "uint256" },
];
