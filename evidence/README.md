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

Only the Base Sepolia run writes the files above.

## Added on 20 October

Each folder below was copied or written once, by the script named, and is kept as it was written.

| folder or file | written by | what it shows |
|:--|:--|:--|
| `domestic-anvil/` | `scripts/run_demo.py --network anvil --live`, with Kimi K3 planning (decision E-30) | the 16 scenarios with no model from outside China: Kimi K3 plans, Qwen audits, 17 of 17 checks. Its action log names `kimi-k3`, `qwen3.8-max` and the rules sentinel, and no Anthropic model |
| `fisco/` | `scripts/fisco_demo.py`, after `scripts/fisco_up.sh` and the fixture (decision E-31) | the unchanged vault on FISCO BCOS 3.17.1, WeBank's consortium chain: 56 of 56 fixture transactions, then 5 of 5 checks (a routine payout, the tier, `TrusteeRequired`, `NotAllowlisted`, `SameLineage`) |
| `erc8004.json` | `scripts/register_agents.py` (decision E-32) | the planner, the auditor and the sentinel as ERC-8004 agents 10302, 10303 and 10304 on Base Sepolia, each bound to the key the vault counts by that key's own signature. `python scripts/register_agents.py --check` reads them back |
| `static-analysis/slither.json` | Slither 0.11.6 | the 11 findings on `contracts/src/` and nothing more; `docs/static-analysis.md` triages each one |

The red team's run with Kimi K3 is in `redteam/results/domestic-kimi/`, beside the pre-registered final run.
