# Lane B handoff: agent wallet backend

Branch `lane/backend`. It is cut from lane C's first commit, so it holds lane A's contracts and lane C's demo data. Built in the cloud session on 18 October 2026, with no model keys: everything ran in dry-run mode.

## What is built

| task | status | where | how it was checked |
|:--|:--|:--|:--|
| B1 provider factory | done in dry-run; live calls not made | `models.py`, `providers/` | `test_models.py`; `test_live.py` skips without keys |
| B2 EIP-712 | done | `eip712.py` | matches `shared/vectors.json` byte for byte (`test_eip712.py`) |
| B3 chain client | done | `chain.py` | routine payout executes; a forced payout is mined and reverted on Anvil (`test_chain.py`) |
| B4 sentinel | done | `sentinel/` | every rule tested; the service signs a valid payout (`test_sentinel.py`) |
| B5 auditor | done in dry-run; live Qwen call not made | `auditor/` | case file has no personal data; integrity check; fails closed (`test_auditor.py`) |
| B6 quarantined reader | done | `reader.py` | the injection documents set the flag and the legitimate ones do not (`test_reader.py`) |
| B7 planner | done in dry-run on Anvil; live run not made | `planner/` | the scripted conversation runs end to end on Anvil (`test_planner.py`) |
| B8 API routes | done | `api.py`, `roles.py`, `app/main.py` | role checks, error shapes, CORS, documents, and the officer and trustee flow over HTTP on Anvil (`test_api.py`) |
| B9 fail-closed queue | done | `queue.py`, `planner/service.py` | checkers down: a batch is queued, then drains when they are back (`test_planner.py`) |
| B10 posture hook | done | `posture.py` | a report above the threshold raises the posture on Anvil, and a routine payout becomes tier 2 (`test_posture.py`) |
| the anonymised usage report (README sections 3, 7.3) | done | `usage.py`, `GET /api/usage` | totals match the books, and no wallet, reference or name appears (`test_usage.py`) |
| B11 recurring payouts (P2) | done in dry-run | `recurring.py`, the `draft` phase in `planner/graph.py` | the schedule drafts the October zakat batch, and only the officer confirms it (`test_recurring.py`) |

All paths are under `backend/app/agentwallet/` unless they say otherwise.

Test results on 18 October 2026:
- `cd backend && python -m pytest`: 101 passed, 4 live tests skipped.
- 12 of the 101 start Anvil with lane A's fixture.
- `gitleaks detect`: no leaks.

The choices lane B made are B-1 to B-15 in `docs/decisions.md`. The API is in `docs/api.md`, and the demo conversation is in `docs/demo-transcript.md`.

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m pytest                      # 101 tests; Anvil and forge must be on PATH for 12 of them
set -a; . ../.env; set +a
../.venv/bin/python -m pytest -m live              # one small paid call per provider whose key is set

# The services, each in its own shell, each with only its own key
AUDITOR_KEY=... ../.venv/bin/uvicorn app.agentwallet.auditor.service:app --port 8101
SENTINEL_KEY=... ../.venv/bin/uvicorn app.agentwallet.sentinel.service:app --port 8102
PLANNER_KEY=... RELAYER_KEY=... ../.venv/bin/uvicorn app.main:app --port 8000
```

`bash scripts/dev_up.sh` (lane E) does all of this against Anvil.

Other modes:
- **Offline.** `AGENTWALLET_DRY_RUN=1` answers every model call from deterministic rules.
- **One process.** `AGENTWALLET_CHECKERS=inprocess` runs the checkers inside the API process.
- **Immune loop hook.** `python -m app.agentwallet.posture status` and `python -m app.agentwallet.posture apply [--report PATH] [--dry-run]`.

## Dry-run and live

In dry-run, each model role answers from rules in its own module, and the reply's model reads `dry-run:<role>`. Decision B-7 lists the rules.
- **The planner** follows a request to an unlisted wallet, as a persuaded model might. This lets the checkers be shown working.
- **The auditor** applies its prompt's decision rules to the case file.
- **The sentinel** never calls a model, so it behaves the same in both modes.

In live mode:
- **Model names.** They come only from `.env`. The code names no model.
- **Refusal fallbacks are on by default.** Claude requests ask for server-side refusal fallbacks. A refused request may then be answered by another model, and the reply names that model. Set `PLANNER_REFUSAL_FALLBACK=off` for red-team runs, so each measured reply comes from the model named in `.env`.

## What needs Hafiz

1. **Model keys and names in `.env`.**
   - Planner: `ANTHROPIC_API_KEY` and `PLANNER_MODEL`.
   - Auditor: `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` and `AUDITOR_MODEL`.
   - Red team: `OPENAI_API_KEY` and `REDTEAM_MODEL`.
   - Prices: `<ROLE>_PRICE_PER_MTOK` for the red-team cost column.
   Then run `python -m pytest -m live`. The three live tests are B1's and B5's live done-when.
2. **The live end-to-end run of B7.** Run the scripted conversation in `docs/demo-transcript.md` against the Anvil fixture with live models. This needs item 1.
3. **Decision A-10.** Step 5 of the transcript, the 1,200 USDC grant, is refused by the vault until the flood relief cap or the grant changes.
4. **Where the backend lives.** Keep this standalone package, or move it into Amanah's backend? Moving it means three swaps, each behind one function (decision B-1):
   - `roles.current_identity` for Amanah's session;
   - `queue.Store` for the durable write queue;
   - `models.CallBudget` for the spending control.

## Next steps for the local session

1. Point lane D's frontend at the real API (`VITE_MOCK_API=0`) and fix any mismatch. The known ones:
   - Add `UNAVAILABLE` to the frontend's verdict type (decision B-4).
   - Use `GET /api/agent/payouts/{proposal_id}` to turn `elevated_pending` rows to `paid`.
   - The real books total 1,810 USDC for 12 households, not the mock's 1,800.
2. Run the live smoke tests and the live B7 run once the keys are in `.env`.
3. Show `GET /api/agent/scheduled` on the officer page, so a drafted monthly batch appears without typing a request.
4. Unify the pydantic pin with lane C. `redteam/requirements.txt` pins 2.11.9 and the backend pins 2.13.5. The release branch's single environment uses the backend's pins.
