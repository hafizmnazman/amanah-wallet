# Lane E handoff: release

Branch `lane/release`, with every lane merged into it. Built in the cloud session on 18 October 2026, on Anvil only: the cloud network cannot reach Base Sepolia, and no keys are set here.

## What is built

| task | status | where |
|:--|:--|:--|
| the local stack | done | `scripts/dev_up.sh` starts Anvil with lane A's fixture, the auditor (8101), the sentinel (8102) and the API (8000) |
| E1 `run_demo.py` | done on Anvil; Base Sepolia not run | `scripts/run_demo.py` drives plan section 10's 16 scenarios and tags every transaction |
| E1 `verify.py` | done on Anvil | `scripts/verify.py` re-checks an executed payout from the chain alone |
| E2 evidence | the tools are done; the Base Sepolia run is not | `scripts/evidence_pack.py`, `evidence/README.md` |
| browser checks on the real stack | done | `frontend/playwright.stack.config.ts`, `frontend/e2e-stack/` |
| E3 documents | drafted; the numbers wait on the runs | `docs/technical-documentation.md`, `docs/security-self-assessment.md` |
| E4 README | audited, not changed | `docs/readme-audit.md`: 17 claims to fix, and 24 fill markers with values |
| E5 deck and video, E6 package | not started | |

Results on Anvil in dry-run, 18 October 2026:
- **`python scripts/run_demo.py --network anvil`: 16 of 17 checks pass.**
  - Scenarios 1 to 6 and 8 to 16 behave as the plan says.
  - Scenario 7 is refused by the vault with `BeneficiaryCapExceeded`: the 1,200 USDC grant is above the 600 USDC cap, decision A-10.
  - The self-check passes: `verify.py` passes on all 14 executed payouts and fails on an edited one.
  - The run sends 83 transactions, every one tagged with its scenario, and the action log verifies.
- **The browser checks against the real stack pass (2 of 2).** The scripted conversation pays 11 households through the HTTP auditor and sentinel. With the posture raised, a payout waits for a trustee and is paid once the trustee page signs it.
- **The dev stack answers over HTTP.** `bash scripts/dev_up.sh` came up, and a flood relief batch of 8 was paid through it.

The choices behind these are E-1 to E-8 in `docs/decisions.md`.

## How to run

```bash
bash scripts/dev_up.sh                                     # the stack on Anvil, dry-run; --live uses .env's model keys
python scripts/run_demo.py --network anvil                 # 16 scenarios, self-checking; evidence in evidence/anvil-demo/
python scripts/run_demo.py --network anvil --keep          # leaves the chain running, for verify.py by hand
python scripts/verify.py <txHash> --rpc-url <rpc> --vault <vault>
python scripts/verify.py --csv evidence/transactions.csv   # every executed payout in the file
python scripts/evidence_pack.py                            # evidence/amanah-evidence-pack.zip
cd frontend && npx playwright test --config playwright.stack.config.ts
```

`PYTHON` picks the interpreter for `dev_up.sh`; the default is `.venv/bin/python`. The stack's browser checks use ports 8400 to 8402, 8845 and 5176, so they do not disturb a running dev stack.

## What needs Hafiz

1. **The Base Sepolia run.** After the A6 deploy, fill `.env` and run `python scripts/run_demo.py --network base-sepolia`. Then build the pack with `python scripts/evidence_pack.py` and commit `evidence/`.
   - **ETH for gas.** These keys send transactions and need Base Sepolia ETH: the relayer (most of them), the auditor and the sentinel (refusal anchors), the posture oracle (scenario 14 and the log head), the guardian (scenario 16) and the planner (scenario 12). Trustees only sign.
   - **USDC for the donor.** Scenario 5 deposits 5,000 USDC from `DONOR_KEY` (else `RELAYER_KEY`). The scenarios then pay out about 3,700 USDC: 1,650 in scenario 6, 1,200 in scenario 7, 398 in scenario 13 and 450 in scenario 15.
   - **Decision needed.** Check how much test USDC the Circle faucet gives per request. If it is far less than 5,000, choose one: lower the demo's amounts, or deploy MockUSDC on Base Sepolia, which changes `USDC_ADDRESS` in plan section 9.
2. **Decision A-10 for scenario 7.** Once the flood relief cap or the grant changes, the demo's scenario 7 should pass.
3. **The video and the deck (E5).** Use `docs/demo-transcript.md` for the chat steps and the proof page for the transactions.

## Next steps for the local session

1. After A6, run the demo on Base Sepolia once, check `verify.py --csv evidence/transactions.csv`, build the pack and commit it.
   - The Base Sepolia path was rehearsed on 18 October against Anvil running with chain id 84532. The real `Deploy.s.sol` wrote `deployments/84532.json`, and `run_demo.py --network base-sepolia` gave the same 16 of 17 as on Anvil.
   - Run it once per deployment. A second run the same day skips the setup steps, but the payout scenarios then fail by design: the day's spend, the 30-day caps and the payout ledger already count the first run's payouts. For a clean rerun, deploy again or wait for the next vault day (08:00 in Kuala Lumpur).
2. E3: fill the `[[fill]]` markers in `docs/technical-documentation.md` and `docs/security-self-assessment.md` once the runs are done.
3. E4: merge `docs/submission-readme.md` into `README.md`. Then run plan task E4's two checks: the `[[fill` search must print nothing, and the dash count must print 0 for every file.
4. E6: choose a licence, open every link from a logged-out browser, run `gitleaks detect`, and send the email before Tuesday 20:00.
