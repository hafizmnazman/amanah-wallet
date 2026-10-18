# Handoff

The cloud session's record of what is built, what needs Hafiz, and what comes next. A new session reads this first, then `CLAUDE.md`, then `IMPLEMENTATION_PLAN.md`.

Last updated: Sunday 18 October 2026, 19:10 Malaysia time. The most complete copy of this file will be on `lane/release` once the lanes are merged there; earlier copies on other branches may be older.

## Branches

| branch | lane | state |
|:--|:--|:--|
| `lane/contracts` | A: contracts | A1 to A5 done. A6 (Base Sepolia deploy) waits on Hafiz |
| `lane/redteam` | C: red team, demo data | In progress in the cloud session |
| `lane/backend` | B: signers, planner, chain client, API | In progress in the cloud session |
| `lane/frontend` | D: frontend | In progress in the cloud session |
| `lane/release` | E: scripts, evidence, docs; all lanes merged | To come |
| `main` | | Untouched. Lanes merge into it in the order A, B, C, D, E |

To get every branch locally:

```bash
git fetch origin
for b in contracts backend redteam frontend release; do git branch --track "lane/$b" "origin/lane/$b" 2>/dev/null; done
git checkout lane/release && git submodule update --init --recursive
```

Each lane writes its own notes in `docs/handoff/lane-<letter>.md`: what is done, how to run it, what is open.

## Needs Hafiz

1. **Deploy and verify the vault on Base Sepolia (task A6).** The plan's gate was Sunday 22:00. The cloud network blocks every Base Sepolia RPC and `api.etherscan.io`, and no keys are set here, so run it locally:
   ```bash
   git checkout lane/contracts && git submodule update --init --recursive
   cd contracts && set -a && source ../.env && set +a
   forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify
   ```
   It needs `RPC_URL`, `BASESCAN_API_KEY` (an Etherscan API key; the multichain API covers Basescan), `TRUSTEE1` to `TRUSTEE3` and `GUARDIAN` as addresses or as keys, and `RELAYER_KEY` with about 0.01 Base Sepolia ETH (deployment uses 3,377,006 gas). Commit `contracts/deployments/84532.json` afterwards.
2. **Decide scenario 7's numbers.** The 1,200 USDC flood grant is above the flood relief per-beneficiary cap of 600 USDC, so it reverts with `BeneficiaryCapExceeded` before a trustee can sign. Recommended: raise that cap to 1,500 USDC. Alternative: a grant between 301 and 600 USDC. Details in `docs/decisions.md`, entry A-10.
3. **Keys for live model runs.** Everything model-facing is being built with a dry-run mode. Live runs need `ANTHROPIC_API_KEY` (reachable from the cloud), `DASHSCOPE_API_KEY` and `OPENAI_API_KEY` or `GROQ_API_KEY` (their hosts are blocked from the cloud), model names in `.env`, and `INSTITUTION_HMAC_KEY` for the beneficiary id hashes.
4. **Commit identity.** Commits from the cloud session are authored as `Claude <noreply@anthropic.com>`, the container's git identity. CLAUDE.md asks for no AI credit in messages; decide whether the author field matters too.

## Done

### Lane A: contracts (`lane/contracts`)

- `contracts/src/AmanahVault.sol` and `IAmanahVault.sol` (plan sections 3.1 and 3.2), Foundry 1.7.1, solc 0.8.26, OpenZeppelin Contracts v5.7.0.
- 109 tests: 86 unit and fuzz, 2 EIP-712 vector, 13 demo-scenario and 8 invariant (256 runs of 64 calls). Each of 12 planted bugs is caught. Record in `docs/contract-tests.md`.
- `shared/abi/`, `shared/eip712.json`, `shared/vectors.json` (eth-account reproduces every digest and signature), `shared/fixture-data.md`.
- `contracts/script/Deploy.s.sol`, `Fixture.s.sol` (Anvil), `anvil_smoke.sh` (scenarios 6, 10, 11, 12 and 16 with cast).
- Decisions the plan left open: `docs/decisions.md`, entries A-1 to A-11. Paths: `docs/PATHS.md`.

Verify: `cd contracts && forge test` (109 pass). On Anvil: `anvil`, then `forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8545 --broadcast`, then `bash script/anvil_smoke.sh`.

## Next

Filled in as the lanes land.
