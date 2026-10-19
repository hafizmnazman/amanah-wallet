# CLAUDE.md

Amanah: an autonomous agent wallet for money held in trust, built for an agent-wallet competition. Deadline Tuesday 20 October 2026, 23:59 UTC+8. Read `IMPLEMENTATION_PLAN.md` for the work, and `docs/PATHS.md` for where things are in this repository.

## How to work here

- You are one of several parallel sessions. Work only in the lane you were assigned, on that lane's branch. Shared files in `shared/` and `docs/api.md` belong to lanes A and B; other lanes read them and never edit them.
- Before coding a task, read its definition of done. Write or extend the test first when the task names one. A task is finished when its tests pass and the existing suites still pass.
- Keep commits small and on your lane branch. Never push to `main` or `operating-books`, never force-push, never rewrite history.
- Commit messages: plain imperative English, no attribution lines, no AI credit of any kind.
- No secrets in the repository: keys only in `.env`, which is git-ignored. Run `gitleaks detect` before every push.
- Do not change the audit agents' prompts (fingerprint `ec02406645ee3f2c`) or the published evaluation results. New prompts for the planner, auditor, sentinel, reader and red-team agent live in new files.
- Do not touch `chaincode/` or the Fabric adapter except to keep their tests green.
- Prefer well-known libraries: OpenZeppelin, Foundry, web3.py, eth-account, FastAPI, LangGraph, the official `anthropic` and `openai` SDKs, viem and wagmi. No obscure packages.
- When a plan step does not match the repository, update `docs/PATHS.md` and continue; do not improvise a new architecture.

## Writing rules for anything a human or judge reads

- English only. No Bahasa Melayu in the UI, prompts, docs or demo.
- No em dashes or en dashes anywhere. Use commas, colons or full stops.
- Specific over vague: numbers with units, names, dates. No claims without a source or a test behind them.
- Plain sentences under 25 words where possible. No throat-clearing, no formulaic closings.

## Running the stack

- `bash scripts/dev_up.sh` starts Anvil, deploys the fixture, and starts the backend, auditor and sentinel.
- Contracts: `cd contracts && forge test`. Invariants: `forge test --match-contract Invariant`.
- Backend: see `docs/PATHS.md` for the test command (baseline 441 tests).
- Red-team: `python -m redteam.run --config redteam/configs/smoke.yaml` for a 5-case run.
- Demo: `python scripts/run_demo.py --network anvil` then `--network base-sepolia`.

## Stop and ask

Stop and ask Hafiz when a task needs a key or funds that are missing, when a shared interface must change, when a baseline test breaks and the fix is not obvious in 20 minutes, or when any provider's spend passes half its budget.
