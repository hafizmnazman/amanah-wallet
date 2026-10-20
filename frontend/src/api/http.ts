import type {
  Alert,
  AmanahApi,
  ChatRequest,
  ChatResponse,
  ConfirmRequest,
  ConfirmResponse,
  CorrectRequest,
  CorrectResponse,
  DocumentResponse,
  Identity,
  PayoutResult,
  PendingPayout,
  PostureResponse,
  ProofRow,
  QueuedPayout,
  ScheduledDraft,
  UsageReport,
  TrusteeSignRequest,
  TrusteeSignResponse,
} from "./types";

/** An HTTP error from the backend: its status, and FastAPI's detail on its own for the screen. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`${status}: ${detail}`);
  }
}

/** Role headers: the standalone stand-in for Amanah's session and role checks, agreed with lane B. */
function headers(identity: Identity, json: boolean): Record<string, string> {
  const h: Record<string, string> = { "X-Amanah-Role": identity.role, "X-Amanah-User": identity.user };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // Keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function httpApi(baseUrl: string): AmanahApi {
  const get = <T>(identity: Identity, path: string) =>
    fetch(`${baseUrl}${path}`, { headers: headers(identity, false) }).then((r) => parse<T>(r));
  const post = <T>(identity: Identity, path: string, body: unknown) =>
    fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers: headers(identity, true),
      body: JSON.stringify(body),
    }).then((r) => parse<T>(r));

  return {
    isMock: false,
    chat: (identity, body: ChatRequest) => post<ChatResponse>(identity, "/api/agent/chat", body),
    correct: (identity, body: CorrectRequest) => post<CorrectResponse>(identity, "/api/agent/correct", body),
    confirm: (identity, body: ConfirmRequest) => post<ConfirmResponse>(identity, "/api/agent/confirm", body),
    pending: (identity) => get<{ items: PendingPayout[] }>(identity, "/api/agent/pending"),
    trusteeSign: (identity, body: TrusteeSignRequest) =>
      post<TrusteeSignResponse>(identity, "/api/agent/trustee-sign", body),
    uploadDocument: (identity, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${baseUrl}/api/documents`, {
        method: "POST",
        headers: headers(identity, false),
        body: form,
      }).then((r) => parse<DocumentResponse>(r));
    },
    proof: (identity) => get<{ rows: ProofRow[] }>(identity, "/api/proof"),
    posture: (identity) => get<PostureResponse>(identity, "/api/posture"),
    queue: (identity) => get<{ items: QueuedPayout[] }>(identity, "/api/queue"),
    payoutStatus: (identity, proposalId) =>
      get<PayoutResult>(identity, `/api/agent/payouts/${encodeURIComponent(proposalId)}`),
    scheduled: (identity) => get<{ items: ScheduledDraft[] }>(identity, "/api/agent/scheduled"),
    usage: (identity) => get<UsageReport>(identity, "/api/usage"),
    alerts: (identity) => get<{ items: Alert[] }>(identity, "/api/alerts"),
  };
}
