# Evidence

What the Base Sepolia run leaves behind for judges and auditors (plan task E2). The files here are written by scripts, never by hand.

| file | written by | what it holds |
|:--|:--|:--|
| `transactions.csv` | every transaction the backend or `scripts/run_demo.py` sends | scenario, description, expected and actual status, block, explorer link, and the vault error for a revert |
| `action-log.jsonl` | the planner, the checkers, the reader, the trustees and the demo script | one hash-chained record per step (plan section 3.5) |
| `demo-summary.json` | `scripts/run_demo.py` | each scenario's expected and actual outcome, the log's head hash and the transaction that anchored it |
| `amanah-evidence-pack.zip` | `scripts/evidence_pack.py` | the files above plus the deployment record, the red-team protocol and report, and the shared interfaces, with a sha256 for each |

## Checking the evidence

- **The action log.** `ActionLog.verify` in `backend/app/agentwallet/evidence.py` recomputes every hash in the chain.
- **The anchor.** The demo anchors the log's head hash with `anchorReport` at the end of the run. The vault's `lastReportHash` holds it until the next anchor.
- **An executed payout.** `python scripts/verify.py <txHash>` re-checks it against the vault's state at the block before. `python scripts/verify.py --csv evidence/transactions.csv` checks every executed payout in the file.

## Local runs

Runs on Anvil write elsewhere, and git ignores those folders:
- `scripts/dev_up.sh` writes to `evidence/anvil/`.
- `scripts/run_demo.py --network anvil` writes to `evidence/anvil-demo/`.

Only the Base Sepolia run writes here.
