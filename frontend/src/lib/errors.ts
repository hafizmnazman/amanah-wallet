import { UserRejectedRequestError } from "viem";

import { ApiError } from "@/api/http";

/**
 * What went wrong, in words the person at the screen can act on. A raw browser error ("Failed to fetch") or
 * an HTTP status prefix never reaches the page.
 */
export const NOT_REACHABLE = "Amanah's backend is not reachable. Nothing was sent. Check it is running, then try again.";
export const ROLE_REFUSED = "Your role cannot do this.";
export const SERVER_TROUBLE = "The vault's API is having trouble. Nothing was sent.";
export const SIGN_CANCELLED = "You cancelled in MetaMask. Nothing was signed; this payout still waits here.";

// Chrome says "Failed to fetch", Firefox "NetworkError when attempting to fetch resource.", Safari "Load failed"
const NETWORK = /failed to fetch|networkerror|load failed|fetch failed|network request failed/i;

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return ROLE_REFUSED;
    if (error.status >= 500) return SERVER_TROUBLE;
    return error.detail;
  }
  if (error instanceof TypeError && NETWORK.test(error.message)) return NOT_REACHABLE;
  if (error instanceof Error) return error.message;
  return String(error);
}

type Walkable = { name?: unknown; code?: unknown; message?: unknown; shortMessage?: unknown; cause?: unknown };

/** The error and its causes, as viem nests them: a wallet's own error sits a few causes down. */
function chain(error: unknown): Walkable[] {
  const out: Walkable[] = [];
  let e = error;
  while (e && typeof e === "object" && out.length < 8) {
    out.push(e as Walkable);
    e = (e as Walkable).cause;
  }
  return out;
}

export function isUserRejection(error: unknown): boolean {
  return chain(error).some(
    (e) =>
      e instanceof UserRejectedRequestError ||
      e.name === "UserRejectedRequestError" ||
      e.code === UserRejectedRequestError.code ||
      (typeof e.shortMessage === "string" && /user rejected|user denied/i.test(e.shortMessage)) ||
      (typeof e.message === "string" && /user rejected|user denied/i.test(e.message)),
  );
}

/** viem's one-sentence shortMessage from the error or one of its causes, if any carries one. */
function shortMessage(error: unknown): string | null {
  const short = chain(error).find((e) => typeof e.shortMessage === "string" && e.shortMessage)?.shortMessage;
  return typeof short === "string" ? short : null;
}

/**
 * A failed trustee signature. viem's message is a multi-line dump of the request; its shortMessage is one
 * sentence, so that is what shows.
 */
export function describeSignError(error: unknown): string {
  if (isUserRejection(error)) return SIGN_CANCELLED;
  if (error instanceof ApiError && error.status === 403 && /not an active trustee/i.test(error.detail)) {
    return "The wallet that signed is not an active trustee in the vault, so nothing was sent.";
  }
  if (error instanceof ApiError || error instanceof TypeError) return describeError(error);
  return shortMessage(error) ?? describeError(error);
}

/** A failed wallet connection, in one sentence like a failed signature. */
export function describeWalletError(error: unknown): string {
  if (isUserRejection(error)) return "You cancelled in MetaMask, so the wallet is not connected.";
  return shortMessage(error) ?? describeError(error);
}
