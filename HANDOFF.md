# Handoff

The record of what is built, what needs Hafiz, and what comes next. A new session reads this first, then `CLAUDE.md`, then `IMPLEMENTATION_PLAN.md`. Each lane's own notes are in `docs/handoff/lane-<letter>.md`. `docs/runbook.md` lists the remaining steps as commands, in order.

Last updated: Monday 19 October 2026, 13:21 Malaysia time, by the local session. The deadline is Tuesday 20 October, 23:59; the plan wants the email sent before Tuesday 20:00.

## Start here

**Continue from `lane/release`, in the WSL run copy** (decision E-17). The cloud session built everything up to `a570c1d` on 18 October. The local session took over on 19 October at 03:10 and works in WSL Ubuntu at `/root/amanah-fintechathon`, where `.env` and the tools live. `docs/PATHS.md` describes the setup. The OneDrive folder on Windows is a second clone, pulled after every push, with nothing installed.

```bash
wsl -d Ubuntu
cd ~/amanah-fintechathon && git pull
bash scripts/test_all.sh            # every suite, about 4 minutes
```

## Branches

| branch | what it holds |
|:--|:--|
| `lane/release` | every lane merged, plus lane E's scripts and all of the local session's work. Continue here |
| `claude/loving-faraday-x5olmb` | the cloud session's own branch, left at `a570c1d` |
| `lane/backend` | lane A, lane C's data (C1), and lane B's backend, at its last merge |
| `lane/redteam` | lanes A and B, plus lane C's harness, at its last merge |
| `lane/frontend` | lane A, plus lane D's frontend, at its last merge |
| `lane/contracts` | lane A |
| `main` | untouched since the first commit. Lanes merge into it in the order A, B, C, D, E, which needs Hafiz |

No history has been rewritten and nothing force-pushed. `gitleaks detect` runs before each push. Decision E-18 plans one rewrite, on Tuesday, before the repository goes public.

## Decided on 19 October

| what | Hafiz's choice | where |
|:--|:--|:--|
| scenario 7's 1,200 USDC grant against the 600 cap | raise the flood relief per-beneficiary cap to 1,500 | A-10, `5c2b078`; the Anvil demo now passes 17 of 17 |
| the token, since Circle's faucet cannot fund a 5,000 deposit | our own TestUSDC, owner-only mint, deployed beside the vault | A-12, `5833d0c` |
| the signer keys | new test wallets generated into `.env`; one faucet transfer to the relayer | E-16, `03a3579` |
| `INSTITUTION_HMAC_KEY` | generated with the keys; the data is regenerated with it | C-13, `233cec2` |
| the project licence | MIT | `61c9e0e` |
| the 128 commits authored as `Claude <noreply@anthropic.com>` | re-author them as Hafiz on Tuesday, before going public | E-18 |
| where the product lives | this repository, standalone, for the competition | the local session's default; say if not |

## Needs Hafiz

In the order they block things:

1. **Fund the relayer and name the chain.** Send about 0.03 Base Sepolia ETH to the relayer, `0xbA1689B264cf9CBa57c2e5127E2c1eF0923ACAfF`. Put `RPC_URL`, a Base Sepolia endpoint, in `.env`. No Etherscan key is needed: its API serves Base Sepolia to paid plans only, so the contracts verify on Blockscout with no key (decision A-13). Then `python scripts/fund_keys.py --send` tops up the other sending keys (runbook step 3).
2. **Model keys and names in `.env`.** The code names no model, and nothing has run live yet.
   - Planner: `ANTHROPIC_API_KEY` and `PLANNER_MODEL`. The local session suggests `claude-opus-5-5`, at $4 and $20 per million input and output tokens (`PLANNER_PRICE_PER_MTOK=4,20`). The Anthropic provider already sends no `temperature`, leaves thinking adaptive, sets effort and asks for refusal fallbacks the way that model needs.
   - Auditor: `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` (Model Studio's international, OpenAI-compatible endpoint) and `AUDITOR_MODEL`, a Qwen model from the console.
   - Red team: `OPENAI_API_KEY`, `REDTEAM_MODEL`, and `AUDITOR_GPT_MODEL` for the matrix's third lineage.
   - Prices: `<ROLE>_PRICE_PER_MTOK`, for the red team's cost column.
   Then `cd backend && python -m pytest -m live`: four small paid calls, one per model role.
3. **Review the red team's attack seeds (C2).** A person reviews every seed before it counts (`redteam/protocol.md`). All 44 drafts wait in `redteam/gallery/drafts/`: the cloud session's 28 and the local session's 16, 4 or more in each of the ten classes. `REVIEW.md` there has one row per seed and the checks already run. Move each file up one folder once it reads right.
4. **Choose how C3, the mutation agent, gets done.** The safety classifier stopped the local session on it too (decision C-14). Either write `redteam/mutate.py` by hand, or run the full run on the reviewed seeds alone and say so in the protocol before committing it.
5. **The red-team protocol (C6).** Fill the model names and case counts in `redteam/protocol.md` and commit it before the full run. Then put that commit's hash in the README.
6. **Refusal fallbacks off for red-team runs.** Set `PLANNER_REFUSAL_FALLBACK=off` in `.env` for the full run, so each measured reply comes from the model named there (decision B-6).
7. **A MetaMask trustee for D3.** Import `TRUSTEE1_KEY` from `.env` into MetaMask, on Base Sepolia. It needs no ETH. Then set `VITE_VAULT_ADDRESS` and `VITE_CHAIN_ID=84532` in `frontend/.env.local`.
8. **Check two scenario readings.**
   - Scenario 9's REJECT comes from the sentinel's frequency and structuring rules: the household was paid hours earlier, in scenario 6 (decision E-4).
   - Scenario 14 uses a summary labelled as fabricated for the demo when no real red-team result is above the threshold (E-5).
9. **The go for the re-authoring, on Tuesday.** One `git filter-repo` run and one force-push of every branch, after the merge into `main` and before the repository goes public (E-18).

## Model budget, estimated 19 October

Hafiz has about $100 of Anthropic credit, $10 of OpenAI credit and none on Qwen. The calls were counted in dry runs of the full red-team set (44 seeds and 20 legitimate cases) and of the demo. Tokens are estimated at 3 characters a token. Output assumes 1,500 tokens per Claude call (thinking at effort high included), 1,000 per GPT call and 300 per Qwen call.

| provider | calls | estimated cost | budget |
|:--|:--|:--|:--|
| Anthropic, `claude-opus-5-5` at $4 and $20 per million tokens | red team 131 (planner 64 at about 3,500 input tokens each, control auditor 60, reader 7); each demo run 8 | red team about $5, up to $9; the demo runs, split screen and video about $3 | stop at $50, half the credit (CLAUDE.md) |
| OpenAI, the GPT auditor | red team 60 at about 630 input tokens each | under $1 on a mid-tier model at $2 and $10; a flagship at $10 and $50 would cost about $3 to $8 | stop at $5 |
| Qwen, the auditor | red team 60; each demo run 16 | under $1 at `qwen-plus` or `qwen-max` prices, and inside Model Studio's free 1 million tokens per model, Singapore region | no credit; the free quota covers it |

- A mutated set of 3 per seed would about triple the red team's calls and cost.
- Set `DAILY_MODEL_CALL_CAP=600`. The runner stops at 80% of it, well above the run's 251 calls.
- The 5-case smoke run, with the `<ROLE>_PRICE_PER_MTOK` prices set, measures the real cost per case before the full run.
- The rest is free: testnet ETH from a faucet, an RPC endpoint's free plan, and verification on Blockscout, which needs no key (decision A-13).

## What is built

| lane | done | not done | notes |
|:--|:--|:--|:--|
| A contracts | A1 to A5, and the demo token (A-12) | A6, the Base Sepolia deploy | `docs/contract-tests.md` |
| B backend | B1 to B11, in dry-run | live model runs | `docs/handoff/lane-b.md`, `docs/api.md` |
| C red team | C1 with the institution's key; C2's format, legitimate set and 44 draft seeds; C4, C5 with the GPT signer, C6 draft; C8 without mutation | C2's review, C3 mutation, C7 full run | `docs/handoff/lane-c.md`, `redteam/protocol.md` |
| D frontend | D1 to D6, standalone | D3's MetaMask run on Base Sepolia | `docs/handoff/lane-d.md` |
| E release | dev stack, E1 on Anvil at 17 of 17, E2 tools, browser checks on the real stack, E3 drafts, E4's fixes as a patch, E5's deck builder, split screen and shot list, E6's gate and email draft, the test-wallet scripts | the Base Sepolia run, E3's numbers, E4 to E6 with real numbers, the video | `docs/handoff/lane-e.md` |

What works end to end today, on Anvil, in dry-run:
- **The officer's conversation.** It pays 11 households through the separate auditor and sentinel services and the vault: in the browser, over HTTP and from the demo script.
- **An elevated payout.** Scenario 7's 1,200 USDC grant waits for a trustee, and the trustee page signs and pays it.
- **Refusals.**
  - An induced transfer is refused, and both checkers anchor their refusals.
  - A prompt-injected letter is flagged, and the second payout it asks for is refused and anchored.
  - Forced, same-lineage and planner-governance attacks are mined and reverted with the vault's errors.
- **Structuring.** It is stopped at the per-household cap.
- **The sentinel's history.** It counts the vault's own payout events, so a lost state directory cannot hide a payout made earlier (decision B-17).
- **One evidence chain across processes.** The API, the auditor and the sentinel append to one hash-chained log under a file lock (decision B-18).
- **The immune loop.** It raises the posture, and two trustees lower it again.
- **An override.** It cites an anchored refusal.
- **A pause.** It blocks payouts until two trustees unpause.
- **Evidence.** Every transaction is tagged in `transactions.csv`. The action log is hash-chained, and its head is anchored on-chain. `verify.py` re-checks every executed payout from the chain.
- **The red-team pipeline.** It runs S1 to S5 with a paired cache and writes a report with Wilson intervals, McNemar tests and the joint-failure matrix.
- **Recurring payouts.** The books' monthly schedule drafts the zakat batch as a plan card, and only the officer confirms it (plan task B11).
- **How each fund was used.** A public page and route give totals by programme and month, with no recipient and no wallet (decision B-15).
- **The test wallets.** `scripts/new_keys.py` and `scripts/fund_keys.py` fill and fund them (decision E-16).

## Test results, 19 October 2026, in WSL

| suite | command | result |
|:--|:--|:--|
| contracts | `cd contracts && forge test` | 112 passed: 86 unit and fuzz, 2 vector, 13 scenario, 8 invariant, 3 demo token |
| backend | `cd backend && python -m pytest` | 133 passed, 4 live skipped; 25 of them start Anvil |
| red team | `python -m pytest -c redteam/pytest.ini redteam/tests` | 25 passed; 1 starts Anvil |
| release scripts | `python -m pytest -p no:cacheprovider scripts/tests` | 29 passed; 3 start Anvil |
| frontend unit | `cd frontend && npm test` | 24 passed |
| frontend browser, mock | `cd frontend && npx playwright test` | 14 passed |
| frontend browser, real stack | `npx playwright test --config playwright.stack.config.ts` | 3 passed |
| demo on Anvil | `python scripts/run_demo.py --network anvil` | 17 of 17 checks |
| the Base Sepolia path, rehearsed on Anvil as chain 84532 | runbook steps 3, 4 and 7 in a throwaway clone (decision E-19) | 17 of 17 checks, 15 of 15 payouts verified, 93 transactions, 14.9 million gas |
| secrets | `gitleaks detect` | no leaks |

The first run on this machine failed one browser check: on a 390 px phone the trustee page scrolled sideways by 11 px. The plain-words summary names the beneficiary's wallet in full (decision B-10), and the paragraph could not break inside the address. DejaVu Sans, the fallback font here, is wider than the cloud machine's. The summary now wraps anywhere (`5a2e62a`).

## Known gaps and incidents

- **No live model call has run.** Every model result so far is dry-run. The dry-run planner follows explicit transfer requests on purpose, so the checkers can be shown working; it is not a model.
- **Not built:**
  - C3's mutation agent, which the safety classifier stopped in both sessions (decision C-14);
  - E3's numbers, the README's final fill, the video, and the package;
  - the Amanah integration, out of scope for the competition.
- **Drafted, waiting on the runs:** the deck (`docs/deck/`, built by `scripts/build_deck.py`), the video shot list (`docs/video-shot-list.md`) and the submission email (`docs/submission-email.md`).
- **A failing test was pushed once.** On `lane/backend`, commit `453c361` went out while a chain test failed about one run in three. Commit `1974068` fixed it (decision B-12).
- **Two reviews on 18 October found thirteen faults, all fixed** with a test each that failed before the fix (decisions B-20, B-21, C-12, E-14 and E-15).
- **The cloud network blocked** Base Sepolia RPCs, Etherscan, and the Qwen and OpenAI hosts. The local session has none of those limits.

## For the README (task E4)

`docs/readme-audit.md` checks `docs/submission-readme.md` against the build. Its fixes are ready as `docs/patches/readme-e4-fills.patch`, applied in runbook step 9 with `scripts/fill_readme.py`. After the patch, the README's two USDC lines need the demo token's address and the reason it is not Circle's (decision A-12). `bash scripts/test_all.sh` is the "one command" the README asks for.

## Next steps, in order

1. Hafiz: fund the relayer, then put `RPC_URL` and the model keys in `.env` (items 1 and 2).
2. Hafiz: review the 44 draft seeds with `redteam/gallery/drafts/REVIEW.md`, and choose how C3 gets done (items 3 and 4).
3. Deploy the token and the vault on Base Sepolia, verified (runbook step 4). Before each paid step, `python scripts/preflight.py --stage deploy` (then `demo`, `models`, `redteam`) names what is still missing. It sends nothing.
4. Live models: `pytest -m live`, then `python scripts/run_demo.py --network anvil --live` (step 5).
5. Red team: promote the reviewed seeds, settle C3, commit the protocol, then the full live run into `redteam/results/final/` (step 6).
6. The Base Sepolia demo, `verify.py` and the evidence pack (step 7).
7. The frontend with a MetaMask trustee, and the video clips (step 8).
8. The documents, the README and the deck with the real numbers (step 9).
9. `python scripts/presubmit.py --links --verify` with no FAIL, the merge into `main`, the re-authoring, the public repository and the email (step 10).
