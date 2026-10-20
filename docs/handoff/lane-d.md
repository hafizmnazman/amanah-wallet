# Lane D: frontend

Branch `lane/frontend`, cut from `lane/contracts`. Built in the cloud session on 18 October 2026. Everything lives in `frontend/`.

## What is built

The plan says to reuse the Amanah Vite app, which is not in this repository. So this is a standalone Vite + React 18 + TypeScript + Tailwind 4 app, written as portable pieces the local session can move into the Amanah app.

| Task | Where | What |
|:--|:--|:--|
| D1 chat panel | `src/components/chat/ChatPanel.tsx`, `ReaderFieldsCard.tsx` | Message list, input, document upload with the reader's typed fields and an injection warning, clarification chips |
| D2 plan and verdict cards | `src/components/plan/` | Plan card with household rows, total, tier preview and Confirm; after confirm, one row per payout with planner, auditor (labelled Qwen) and sentinel cards, status and explorer link |
| D3 trustee signing | `src/pages/TrusteePage.tsx`, `src/components/trustee/` | Pending payouts with the plain-words summary beside fields decoded from `typed_data` itself. Signs with wagmi `signTypedData` through MetaMask, then posts to `/api/agent/trustee-sign`. A dev-only "Sign with Local Trustee Key" button when `VITE_DEV_SIGNING=1` |
| D4 proof, posture, queue | `src/pages/ProofPage.tsx`, `QueuePage.tsx`, `src/components/PostureBanner.tsx` | 16 proof rows with explorer links, a posture banner on every page above level 0, the fail-closed queue |
| D5 browser checks | `src/**/*.test.ts`, `e2e/` | 20 Vitest unit tests, 11 Playwright checks including 390 px phone layouts |
| D6 fund switcher | `src/components/Layout.tsx`, `src/session/FundContext.tsx` | The three funds; the chat defaults to the selected one |

**The trustee screen refuses to let a trustee sign blind (`src/lib/typedData.ts`, `src/lib/summaryCheck.ts`).** Before the Sign buttons enable, it checks:
- the domain name and version;
- the chain against `VITE_CHAIN_ID`;
- the vault against `VITE_VAULT_ADDRESS`;
- the Payout type, field by field, against `shared/eip712.json`;
- that the summary's first USDC amount and any wallet it names match the signed fields.

Any mismatch shows "Do not sign" and disables signing.

**Cross-lane checks in the unit tests.** `src/lib/eip712.test.ts` fails if the app's copy of the types drifts from `shared/eip712.json`. `src/lib/typedData.test.ts` asserts that viem's digest for the vector payout equals the vault's, from `shared/vectors.json`.

## How to run and test

```bash
cd frontend
npm ci
cp .env.example .env.local      # then edit; never commit .env.local
npm run dev                     # http://127.0.0.1:5173
VITE_MOCK_API=1 npm run dev     # the scripted demo with no backend
npm run build                   # type-check and production build
npm test                        # 20 unit tests
npx playwright test             # 11 browser checks; starts its own mock-mode dev server on port 5174
```

Results on 18 October 2026: `npm ci` 581 packages, build clean, 23 of 23 unit tests, 14 of 14 Playwright checks.

Results on 19 October 2026, in the local session's WSL copy: build clean, 24 unit tests, 14 of 14 Playwright checks on the mock and 3 of 3 on the real stack. The first run failed the 390 px trustee check by 11 px: the plain-words summary names the wallet in full, and the paragraph could not break inside it in this machine's wider fallback font. `wrap-anywhere` on the summary fixed it (`b314612`).

Results later on 19 October, after the redesign (decision E-26) and Title Case labels (E-28): type check clean, 25 unit tests, 14 of 14 Playwright checks on the mock, 3 of 3 on the real stack, and 4 of 4 in the README shots run. Labels are in Title Case; data such as programme names is title-cased only for display, through `titleCase()` in `src/lib/utils.ts`.

## What is mocked

`VITE_MOCK_API=1` swaps the HTTP client for `src/api/mock.ts`, an in-browser stand-in for lane B's backend. It plays the scripted demo:
- the October zakat request gets a clarifying question;
- the plan card has 12 households, 1,810 USDC, the same as the real books;
- "leave out household 12" leaves 11 households, 1,650 USDC, inside scenario 13's window;
- confirming pays all 11, with three verdicts each.

It also serves:
- the 1,200 USDC flood relief emergency grant pending for the trustee;
- a bursary batch that previews as elevated;
- 16 proof rows, one queue item, and a posture level that a mock-only button raises.

Mock hashes are zero-padded counters. They are never linked to an explorer, and every screen fed by the mock shows a "Mock data" badge, so a recording cannot pass them off as real. The real HTTP client is `src/api/http.ts`.

## What needs Hafiz

1. After the Base Sepolia deploy (A6), set `VITE_VAULT_ADDRESS` and `VITE_CHAIN_ID=84532` in `frontend/.env.local`. Without the vault address, the trustee page refuses to sign against a real backend, by design.
2. A MetaMask account registered as a trustee, for D3's done-when: an elevated payout completed from the UI in MetaMask. Import `TRUSTEE1_KEY` from `.env`, which `scripts/new_keys.py` filled (decision E-16). It needs no ETH: the trustee signs typed data, and the relayer submits.
3. Done: decision A-10 kept the 1,200 USDC grant and raised the cap to 1,500, so the mock's pending grant stays as it is.
4. Done: the demo ships this standalone app (HANDOFF, 19 October).

## What the backend must match

These conventions were agreed with lane B and are coded in `src/api/http.ts`:
- **Base URL.** From `VITE_API_URL`, default `http://127.0.0.1:8000`. The backend must allow CORS from `http://localhost:5173` and `http://127.0.0.1:5173`.
- **Role headers.** Every request sends `X-Amanah-Role` (`finance_officer`, `trustee`, `guardian` or `external_auditor`) and `X-Amanah-User`. This is the stand-in for Amanah's session and role checks.
- **Corrections.** While a plan card is open and unconfirmed, the officer's next message goes to `POST /api/agent/correct`, not to `/chat`.
- **`typed_data` format.** `PendingPayout.typed_data` must use exactly the `shared/eip712.json` Payout type with the live domain. Integers (`amount`, `nonce`, `deadline`) are decimal strings or safe numbers, and `bytes32` and addresses are `0x` hex.
- **Summary text.** `PendingPayout.summary_text` should name the payout amount first, as "1,200.00 USDC", and include the beneficiary wallet. The trustee page compares both with the signed fields, and a summary with no amount blocks signing. This matters for the Reporter in lane B's task B7.
- **Errors.** Errors as FastAPI `{"detail": "..."}` are shown to the user.

Two additions to plan section 3.3, both now in lane B (`docs/api.md`, decision B-3):
- `POST /api/agent/chat` sends an optional `programme_code` from the fund selector. The backend accepts it and does not use it yet.
- `GET /api/agent/payouts/{proposal_id}` returns a payout's latest result. An `elevated_pending` or `queued` row on the officer page polls it every 5 seconds, so the row turns to paid after a trustee signs (`src/components/plan/PayoutResults.tsx`).

A verdict can also be `UNAVAILABLE` when a checker could not be reached (decision B-4). `src/api/types.ts` includes it.

The officer page also shows the books' scheduled batches (plan task B11, `GET /api/agent/scheduled`) above the chat, each with a Confirm button (`src/components/plan/ScheduledDrafts.tsx`). Nothing is paid until the officer confirms. The mock drafts October's zakat batch.

A "Fund use" page (`src/pages/UsagePage.tsx`, route `/usage`) shows how each fund was used, from the public `GET /api/usage` (decision B-15): totals by programme and month, with no recipient and no wallet.

## Next steps for the local session

1. When lane B's routes (B8) exist, run with `VITE_MOCK_API=0` and fix any mismatch with the real responses.
2. Move the pieces into the Amanah app:
   - Copy `src/api`, `src/lib`, `src/components`, `src/pages` and `src/wallet`.
   - Replace `src/session/IdentityContext.tsx` and the role headers with Amanah's session.
   - Add the four routes to its router.
   - Merge the theme tokens from `src/index.css`.
   - Add the `e2e/` specs to the existing browser suite (186 and up).
3. Complete an elevated payout on Base Sepolia with MetaMask (D3 done-when), and record the clip for the video.

## Proposed rows for shared files

For `docs/PATHS.md`, under a new "Lane D: frontend" heading:

| what | path |
|:--|:--|
| standalone frontend | `frontend/` |
| typed API client, mock backend | `frontend/src/api/` |
| officer, trustee, proof and queue pages | `frontend/src/pages/` |
| EIP-712 decoding and pre-signing checks | `frontend/src/lib/typedData.ts`, `frontend/src/lib/summaryCheck.ts` |

Test commands:

| suite | command | count |
|:--|:--|--:|
| frontend: unit | `cd frontend && npm test` | 23 |
| frontend: browser | `cd frontend && npx playwright test` | 14 |
| frontend: build | `cd frontend && npm run build` | |

For `.env.example`: no change. The frontend's `VITE_` variables live in `frontend/.env.example`. A one-line pointer could be added: `# Frontend variables: see frontend/.env.example`.

## Environment notes

- npm 10.9.4's resolver crashes (`Cannot read properties of null (reading 'edgesOut')`) when building a fresh lockfile for wagmi's peer dependencies. The lockfile was made with `npx npm@11.21.0 install`. `npm ci` with npm 10.9.4 installs from it without trouble.
- `@playwright/test` is pinned to 1.56.1 because it uses Chromium build 1194, the one pre-installed in the cloud container (`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`). Elsewhere, run `npx playwright install chromium` once.
- `npm audit` was not run: the cloud network blocks the audit endpoint. The MetaMask SDK pulled in by wagmi 2.19.5's connectors is marked deprecated upstream. Only the injected connector is used, and the build tree-shakes the rest.

## 20 October

A letter that names no amount blanked the Officer Desk: the reader sends null for a field it did not find, and `ReaderFieldsCard` formatted the null amount. The rows now come from `readerRows` in `src/lib/reader.ts`, which says "not found" for null too, and `ReaderFields` says the API may send null (`d37316c`, two unit tests; the frontend has 27).
