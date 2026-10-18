# Backend API

The agent wallet's HTTP API, from plan section 3.3, as built in `backend/app/agentwallet/api.py`. Lanes A and B own this file. A change to a shape here needs a note in `docs/decisions.md`.

Run it with `cd backend && uvicorn app.main:app --port 8000`. FastAPI also serves the live schema at `/docs` and `/openapi.json`.

## Conventions

- **Roles.** Every route except `/api/health` reads two headers:
  - `X-Amanah-Role`: `finance_officer`, `trustee`, `guardian` or `external_auditor`.
  - `X-Amanah-User`: a user name.
  These headers stand in for Amanah's session and role checks, which are not in this repository (`backend/app/agentwallet/roles.py`).
  - A missing or unknown role answers 401.
  - A role the route does not admit answers 403.
- **Sessions.** A `session_id` is scoped to the caller's `X-Amanah-User`. Another user who sends the same id gets a different conversation.
- **Errors.** Every error is `{"detail": "..."}` with a sentence the frontend can show.
- **Amounts.** `amount_usdc` and `total_usdc` are whole USDC as decimal strings, for example `"150"` or `"1650"`. In typed data, `amount` is in base units (6 decimals) as a decimal string.
- **CORS.** Allowed origins come from `CORS_ORIGINS`, comma-separated. The default is `http://localhost:5173,http://127.0.0.1:5173`.

## Routes in plan section 3.3

| Route | Role | Body | Returns | Errors |
|:--|:--|:--|:--|:--|
| `POST /api/agent/chat` | finance officer | `{session_id, message, document_ids?, programme_code?}` | `{reply, plan_card?, clarification?}` | |
| `POST /api/agent/correct` | finance officer | `{session_id, batch_id, instruction}` | `{reply, plan_card}` | 404: no open plan with that batch id in the session |
| `POST /api/agent/confirm` | finance officer | `{session_id, batch_id}` | `{results: [PayoutResult]}` | 404: as above |
| `GET /api/agent/pending` | trustee | | `{items: [PendingPayout]}` | |
| `POST /api/agent/trustee-sign` | trustee | `{proposal_id, signature}` | `{tx_hash, status}` | 400: unreadable signature. 403: the signer is not an active trustee. 404: no payout waits under that id |
| `POST /api/documents` | finance officer | multipart, field `file` | `{document_id, fields: ReaderFields, injection_flag}` | 413: over 1 MB. 415: not UTF-8 text |
| `GET /api/proof` | any role | | `{rows: [ProofRow]}` from `evidence/transactions.csv` | |
| `GET /api/posture` | any role | | `{level, last_report_hash, raised_at}` | 503: the vault cannot be read |
| `GET /api/queue` | trustee | | `{items: [QueuedPayout]}` | |

Notes on these routes:
- **`programme_code` on chat.** Lane D's fund selector sends it. It is an addition to section 3.3 (decision B-3). The planner does not use it yet, so an ambiguous request still gets the clarifying question the demo shows.
- **Confirm is idempotent.** Confirming the same batch twice returns the first results and submits nothing.
- **Trustee signing.** `trustee-sign` recovers the signer from the EIP-712 signature and checks the on-chain registry for an active `TRUSTEE`. Only then does it append the signature to the stored quorum and call `execute`. The header names the user; the signature decides who signed.
- **Documents.** The reader's fields are kept under `document_id`. A later chat message passes them to the planner in `document_ids`. The raw text never reaches the planner. The action log keeps the sha256 of the upload and the injection signals.
- **Posture with no chain.** When `RPC_URL` or `VAULT_ADDRESS` is unset, `/api/posture` answers level 0 with nulls.

## Routes added for the frontend and the scripts

| Route | Role | Returns |
|:--|:--|:--|
| `GET /api/health` | none | `{status, chain, dry_run, chain_id, vault}`. `scripts/dev_up.sh` waits on it |
| `GET /api/agent/payouts/{proposal_id}` | finance officer, trustee | the latest `PayoutResult` for one payout, so an `elevated_pending` row can turn to `paid` after a trustee signs. 404 when unknown |
| `GET /api/alerts` | trustee, guardian | `{items: [{id, created_at, kind, proposal_id, message, read}]}`. Kinds: `queued`, `drained`, `trustee_needed`, `plan_ready` |
| `GET /api/agent/scheduled` | finance officer | `{items: [{session_id, plan_card}]}`: the caller's drafted scheduled batches, not yet confirmed (plan task B11). Confirm one with `POST /api/agent/confirm` and its `session_id` |

## Shapes

```text
PlanCard      = {batch_id, programme_code, programme_name, fund_name,
                 items: [{household_ref, beneficiary_ref, wallet, amount_usdc}],
                 total_usdc, tier_preview: "routine"|"elevated", notes: [str]}
PayoutResult  = {proposal_id, household_ref, amount_usdc,
                 status: "paid"|"elevated_pending"|"rejected"|"escalated"|"queued"|"reverted",
                 tx_hash?, explorer_url?, verdicts: {planner, auditor, sentinel}, reasons: [str]}
Verdict       = {verdict: "APPROVE"|"REJECT"|"ESCALATE"|"UNAVAILABLE", reasons: [str], input_hash, model,
                 lineage, signed: bool}
PendingPayout = {proposal_id, summary_text, typed_data: EIP712TypedData, decoded_fields: {...}, verdicts, tier}
ReaderFields  = {applicant_ref?, requested_amount_usdc?, programme_code?, dates: [str], free_text_present: bool}
ProofRow      = {scenario, description, expected, tx_hash, status, block: int|null, explorer_url}
QueuedPayout  = {proposal_id, reason, queued_at, missing: "auditor"|"sentinel"|"chain"|"funds"}
Posture       = {level: int, last_report_hash: "0x..."|null, raised_at: unix seconds|null}
```

Details the frontend relies on:
- **`UNAVAILABLE`.** A verdict is `UNAVAILABLE` when a checker could not be reached. The payout is then `queued` (decision B-4). Section 3.3 lists only three verdict values.
- **`typed_data`.** It is exactly the `Payout` type in `shared/eip712.json`, with the live domain:
  - `chainId` is a number and `verifyingContract` is the vault.
  - `amount`, `nonce` and `deadline` are decimal strings; `bytes32` fields and addresses are `0x` hex.
  - `Payout.from_strings(typed_data["message"])` rebuilds the payout in Python.
- **`summary_text`.** It is written from the decoded typed data, never from the conversation (`backend/app/agentwallet/reporter.py`):
  - It starts with the amount, as in `Pay 1,200.00 USDC from the ...`.
  - It names the beneficiary wallet in full.
  - It ends with the tier's rule, for example "one trustee must co-sign".
  - The trustee page compares the first amount and the wallet with the signed fields.
- **`decoded_fields`.** Keys: `programme_code`, `programme_name`, `fund_name`, `beneficiary_wallet`, `beneficiary_ref`, `household_ref`, `amount_usdc`, `amount_units`, `proposal_id`, `evidence_hash`, `nonce`, `deadline`.

## Statuses

| status | meaning |
|:--|:--|
| `paid` | executed on-chain; `tx_hash` and `explorer_url` are set |
| `elevated_pending` | the vault rates it tier 2; it waits in `/api/agent/pending` for one trustee |
| `rejected` | a checker said REJECT, or the vault refuses it before submission (the reason names the vault's error) |
| `escalated` | a checker said ESCALATE: a person must look at it |
| `queued` | fail-closed: a checker or the chain was unreachable, or the planner had no key. The queue retries every `QUEUE_RETRY_SECONDS` (default 60) |
| `reverted` | submitted and mined, but the vault reverted it; `reasons` names the error |

## Signer services (plan section 3.4, localhost only)

`POST /verdict` on the auditor (port 8101) and the sentinel (port 8102). Each also serves `GET /health`.

- **Request.** `{payout: Payout with every field as a string, proposal_id, programme_code, features?}`.
- **Sentinel extras.** The sentinel also takes:
  - `batch`: the other payouts in the batch, as strings;
  - `spent_today`: base units, from the vault's `spentToday`.
  It computes its own features from the books and the batch, so it does not have to trust the caller's.
- **Response.** `{verdict, reasons: [str], input_hash, model, lineage, signature?, anchor_id?, anchor_tx?}`.
  - `signature` is present only on APPROVE: the service's EIP-712 signature of the payout.
  - `anchor_id` and `anchor_tx` are present when a REJECT or ESCALATE was anchored on-chain with `anchorDecision`.
  - Anchoring needs `RPC_URL`. Set `AUDITOR_ANCHOR=0` or `SENTINEL_ANCHOR=0` to turn it off.
- **Unreachable checker.** When a checker cannot be reached or every model behind it fails, the planner records `UNAVAILABLE` and queues the payout.

`AGENTWALLET_CHECKERS=inprocess` runs both checkers inside the API process instead of over HTTP. The tests and `scripts/run_demo.py --network anvil` use it.
