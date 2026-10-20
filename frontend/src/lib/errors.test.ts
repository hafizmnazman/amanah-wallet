import { BaseError, UserRejectedRequestError } from "viem";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/http";

import { describeError, describeSignError, describeWalletError, NOT_REACHABLE, ROLE_REFUSED, SERVER_TROUBLE, SIGN_CANCELLED } from "./errors";

describe("describeError", () => {
  it("names an unreachable backend instead of the browser's words", () => {
    expect(describeError(new TypeError("Failed to fetch"))).toBe(NOT_REACHABLE);
    expect(describeError(new TypeError("NetworkError when attempting to fetch resource."))).toBe(NOT_REACHABLE);
    expect(describeError(new TypeError("Load failed"))).toBe(NOT_REACHABLE);
  });

  it("says a 403 is the role, a 5xx is the API, and keeps other details without the status prefix", () => {
    expect(describeError(new ApiError(403, "This route is for the trustee role."))).toBe(ROLE_REFUSED);
    expect(describeError(new ApiError(500, "Internal Server Error"))).toBe(SERVER_TROUBLE);
    expect(describeError(new ApiError(503, "Service Unavailable"))).toBe(SERVER_TROUBLE);
    expect(describeError(new ApiError(413, "Documents over 1 MB are not read."))).toBe("Documents over 1 MB are not read.");
  });

  it("keeps a plain error's message and a string as it is", () => {
    expect(describeError(new Error("No plan with that batch id in this chat."))).toBe("No plan with that batch id in this chat.");
    expect(describeError("The typed data cannot be decoded.")).toBe("The typed data cannot be decoded.");
    expect(describeError(new TypeError("x is undefined"))).toBe("x is undefined");
  });
});

describe("describeSignError", () => {
  const rejected = { code: 4001, message: "MetaMask Tx Signature: User denied message signature." };

  it("turns a MetaMask cancel into one plain sentence, however viem wraps it", () => {
    expect(describeSignError(new UserRejectedRequestError(new Error("User rejected the request.")))).toBe(SIGN_CANCELLED);
    expect(describeSignError(new BaseError("Signing failed.", { cause: new UserRejectedRequestError(new Error("denied")) }))).toBe(
      SIGN_CANCELLED,
    );
    expect(describeSignError(rejected)).toBe(SIGN_CANCELLED);
    expect(describeSignError(new Error("User rejected the request."))).toBe(SIGN_CANCELLED);
  });

  it("shows viem's short message, never the multi-line dump", () => {
    const error = new BaseError("The chain is not configured.", { details: "Request Arguments:\n  chain: 84532\nVersion: viem@2" });
    expect(error.message).toContain("\n");
    expect(describeSignError(error)).toBe("The chain is not configured.");
  });

  it("says a cancelled wallet connection in one sentence too", () => {
    expect(describeWalletError(new UserRejectedRequestError(new Error("User rejected the request.")))).toBe(
      "You cancelled in MetaMask, so the wallet is not connected.",
    );
    expect(describeWalletError(new BaseError("Connector not found.", { details: "a\nlong\ndump" }))).toBe("Connector not found.");
  });

  it("says when the signing wallet is not a trustee, and passes other API errors through describeError", () => {
    expect(describeSignError(new ApiError(403, "0xabc is not an active trustee"))).toMatch(/not an active trustee in the vault/);
    expect(describeSignError(new ApiError(502, "Bad Gateway"))).toBe(SERVER_TROUBLE);
    expect(describeSignError(new TypeError("Failed to fetch"))).toBe(NOT_REACHABLE);
  });
});
