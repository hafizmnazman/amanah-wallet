import { describe, expect, it } from "vitest";

import shared from "../../../shared/eip712.json";

import { DOMAIN_NAME, DOMAIN_VERSION, GOVERNANCE_TYPE, PAYOUT_TYPE } from "./eip712";

describe("the app's copy of the EIP-712 types", () => {
  it("matches shared/eip712.json, field by field and in order", () => {
    expect(PAYOUT_TYPE).toEqual(shared.types.Payout);
    expect(GOVERNANCE_TYPE).toEqual(shared.types.Governance);
    expect(DOMAIN_NAME).toBe(shared.domain.name);
    expect(DOMAIN_VERSION).toBe(shared.domain.version);
  });
});
