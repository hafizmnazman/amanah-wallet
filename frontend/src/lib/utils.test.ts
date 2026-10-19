import { describe, expect, it } from "vitest";

import { titleCase } from "./utils";

describe("titleCase", () => {
  it("capitalises a label's words, keeps joining words small and leaves codes alone", () => {
    expect(titleCase("Ipoh fakir monthly aid")).toBe("Ipoh Fakir Monthly Aid");
    expect(titleCase("splitting under the cap")).toBe("Splitting Under the Cap");
    expect(titleCase("the vault: a trustee co-signs")).toBe("The Vault: A Trustee Co-Signs");
    expect(titleCase("pay ZKT-IPOH-FAKIR-M for October")).toBe("Pay ZKT-IPOH-FAKIR-M for October");
    expect(titleCase("one of 12 in")).toBe("One of 12 In");
  });
});
