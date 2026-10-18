import { describe, expect, it } from "vitest";

import { formatBaseUnits, formatTotal, formatUsdc, parseUsdc } from "./usdc";

describe("formatBaseUnits", () => {
  it("formats 6-decimal base units with thousands separators", () => {
    expect(formatBaseUnits(1_200_000_000n)).toBe("1,200.00");
    expect(formatBaseUnits("150000000")).toBe("150.00");
    expect(formatBaseUnits(0n)).toBe("0.00");
    expect(formatBaseUnits(1n)).toBe("0.000001");
    expect(formatBaseUnits(1_500_000n)).toBe("1.50");
    expect(formatBaseUnits(100_000_000_000_000n)).toBe("100,000,000.00");
  });

  it("keeps significant decimals and drops trailing zeros past two", () => {
    expect(formatBaseUnits(199_123_400n)).toBe("199.1234");
  });
});

describe("parseUsdc", () => {
  it("parses whole-USDC amounts exactly", () => {
    expect(parseUsdc(150)).toBe(150_000_000n);
    expect(parseUsdc("1,200.00")).toBe(1_200_000_000n);
    expect(parseUsdc("0.000001")).toBe(1n);
    expect(parseUsdc(199.5)).toBe(199_500_000n);
  });

  it("refuses text and more than 6 significant decimals", () => {
    expect(() => parseUsdc("abc")).toThrow();
    expect(() => parseUsdc("1.0000001")).toThrow();
  });
});

describe("formatUsdc", () => {
  it("formats API amounts", () => {
    expect(formatUsdc(1650)).toBe("1,650.00");
    expect(formatUsdc("140")).toBe("140.00");
  });
});

describe("formatTotal", () => {
  it("shows a total, or says it is not shown when the usage report hides it", () => {
    expect(formatTotal("5850.00")).toBe("5,850.00 USDC");
    expect(formatTotal(null)).toBe("not shown");
    expect(formatTotal(null, "total not shown")).toBe("total not shown");
  });
});
