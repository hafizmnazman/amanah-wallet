# Handoff

The record of what is built, what needs Hafiz, and what comes next. A new session reads this first, then `CLAUDE.md`, then `IMPLEMENTATION_PLAN.md`. Each lane's own notes are in `docs/handoff/lane-<letter>.md`. `docs/runbook.md` lists the remaining steps as commands, in order.

Last updated: Tuesday 20 October 2026, 02:45 Malaysia time, by the planning session. The deadline is Tuesday 20 October, 23:59; the plan wants the email sent before Tuesday 20:00.

## Start here

**Continue from `lane/release`, in the WSL run copy** (decision E-17). The cloud session built everything up to `a570c1d` on 18 October. The local session took over on 19 October at 03:10 and works in WSL Ubuntu at `/root/amanah-wallet`, where `.env` and the tools live. `docs/PATHS.md` describes the setup. The OneDrive folder on Windows is a second clone, pulled after every push, with nothing installed.

```bash
wsl -d Ubuntu
cd ~/amanah-wallet && git pull
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
| the 44 attack seeds | accept the local session's review rather than read every row, to keep the submission on time | C2, `99e552f` |
| plan task C3, the mutation agent | run the red team on the reviewed seeds alone | C-14, protocol `ffa0490` |
| the team | Team Amanah: Abdul Hafiz Bin Mohd Noor Azman and Muhammad Khaidhir Bin Mohd Razin, both Bachelor of Computer Science (Hons.), Universiti Teknologi PETRONAS, 4th Year, 1st Semester; advisor Assoc. Prof. Ts. Dr. Khaironi Yatim Sharif (FSMC, UTP), named on 19 October | the README, the registration form and email; the deck when it is rebuilt |

## Needs Hafiz

In the order they block things:

1. **Done 19 October: funding and the deploy.** No Base Sepolia faucet would pay a fresh address: Coinbase's asked for a phone number, Alchemy's and QuickNode's for ETH on mainnet. Hafiz claimed 0.05 Ethereum Sepolia ETH from Google Cloud's faucet to the relayer, and the local session bridged 0.048 through Base's L1StandardBridge (Sepolia transaction `0xb77d303921b2a3a599f889ebcd521c4d6d7b5030cd4022794bbdbe724fa6608a`); it reached Base Sepolia in about 5 minutes. `fund_keys.py --send` then topped up the six other sending keys, and both contracts were deployed and verified on Blockscout (see "On Base Sepolia" below).
2. **Done 19 October: model keys and names.** The Anthropic, OpenAI and Model Studio keys are in `.env`, with their prices: planner `claude-opus-5-5`, auditor `qwen3.8-max` without thinking (decision B-23), GPT auditor and red-team role `gpt-6.1-sol`. `pytest -m live` passed 4 of 4, and `run_demo.py --network anvil --live` passed 17 of 17 (E-21). Model Studio answered before Alibaba's identity check finished.
3. **Done 19 October: the seeds (C2).** The local session reviewed all 44 against the four questions in `redteam/gallery/drafts/REVIEW.md`, and Hafiz accepted that review rather than reading every row, to keep the submission on time. They are in `redteam/gallery/` (`99e552f`).
4. **Done 19 October: C3 skipped.** Hafiz chose to run the red team on the seeds alone; the mutation agent stays unbuilt (decision C-14), and can come when the demo is refined for the judges.
5. **Done 19 October: the protocol (C6),** committed on its own before the full run: `ffa0490`. The README cites that hash.
6. **Done 19 October: refusal fallbacks off** in `.env` for the red-team run (decision B-6). It can stay off; the demo does not need fallbacks.
7. **MetaMask for the video's trustee shot.** Add the local chain (RPC http://127.0.0.1:8545, chain id 31337) and import Anvil's account 5, the fixture's trustee 1, a public test key (`docs/video-shot-list.md`). Plan task D3 on Base Sepolia, with `TRUSTEE1_KEY`, is optional now (decision E-25).
8. **Check three scenario readings.**
   - Scenario 9: in dry-run, the REJECT comes from the sentinel's frequency and structuring rules, since the household was paid hours earlier, in scenario 6 (decision E-4). With the live planner, the letter stops at the planner: it declines to pay from a flagged letter with no amount, so nothing reaches a signer (E-21).
   - Scenario 8: with the live planner, the chairman's message also stops at the planner, which refuses it; the checkers' own anchored refusals show in scenario 15.
   - Scenario 14 keeps the summary labelled as fabricated for the demo: the red team's measured joint failure is 0.0%, which raises no posture (E-5).
9. **Done 19 October: the team.** The README, the deck and the email draft name Team Amanah and both members. Still open: the video and deck links (README and email), the members' emails, and the organisers' address and subject format (email).
10. **Record the video** (runbook step 8) from `docs/video-shot-list.md`: the browser shots on the local stack with the live models, the chain shots from the Base Sepolia run on Blockscout, and captions that say which (decision E-25). The split screen and shot 10's posture command were both tried on 19 October.
11. **The go for `main`, on Tuesday.** Proposed: fast-forward `main` to `lane/release` (runbook step 10). It is checked on 19 October in a throwaway worktree: `main` is an ancestor of `lane/release`, which already holds every lane, merged in the order A and B, C, D. Merging lane by lane from `main` instead stops at lane C on a `docs/decisions.md` conflict that `lane/release` resolved on 18 October. Until then a visitor to the repository sees the plan-stage README on `main`, the default branch.
12. **The go for the re-authoring, on Tuesday.** One `git filter-repo` run and one force-push of every branch, after the merge into `main` and before the repository goes public (E-18). The same run replaces the competition's name in old commit messages and file versions, and the merged lane branches are deleted first (E-27).
13. **Approve the UI** (decisions E-26 and E-28, labels now in Title Case as Hafiz asked), at http://localhost:5173 while the local stack runs. The deck and the video wait for it.
14. **Done 20 October, 00:50: the team is registered.** The email went from Hafiz's UTP address with the signed form, both passports and both enrollment letters; the organisers confirm within 48 hours. Everything is kept in the competition folder's `submission/registration/`, outside the repository. The organisers' rules, added beside the brief, make the demo video optional and put the deadline at 23:59 Beijing time.
15. **The final day's plan** is `planning/final-day-plan.md` in the competition folder, written at 02:10 on 20 October (decision E-29). Read it before starting anything. It sets the day's rules (sell hard, prove harder; one source of numbers; the rubric's words as headings; `docs/claims.md` as the gate), lists 42 wow factors with the evidence for each (23 already built and to be surfaced, 11 to build today, 8 of framing), gives every deliverable its upgrade (README first screen and the "twenty-three things" list, technical and security documents as short papers with PDFs, a 15-slide deck in the app's palette with logos, a 4-minute video that is submitted although optional, a hosted demo, a pitch sheet, a benchmark release, a sealed evidence bundle, the email as a cover letter), and schedules three parallel sessions on `lane/final-code`, `lane/final-docs` and `lane/final-media`, merged from 18:00, the email at 21:30. Hafiz decided at 02:30: the Groq key is in `.env`; the three sessions start at once; the real MetaMask signature on Base Sepolia (W34) is in; he records the voice-over; no quote from the advisor. Still open: his UI review at http://localhost:5173, which gates only the deck's screenshots and the video. The local stack is down after the session change, so the media session brings it up first (`bash scripts/dev_up.sh --live`, then Vite with `VITE_DEV_SIGNING=1`). The one UI change the plan asks for is the wordmark, `amanah` to `Amanah`, in `frontend/src/components/Layout.tsx`.

## On Base Sepolia

Deployed and verified on 19 October 2026 from the relayer, `0xbA1689B264cf9CBa57c2e5127E2c1eF0923ACAfF`:

| contract | address | block | record |
|:--|:--|--:|:--|
| TestUSDC, tUSDC (decision A-12) | [`0x3Baa167209d837C663054980f57296c63a93bfa9`](https://base-sepolia.blockscout.com/address/0x3Baa167209d837C663054980f57296c63a93bfa9) | 48313816 | `contracts/deployments/84532-token.json`; 20,000 minted to the donor |
| AmanahVault, the demo's | [`0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5`](https://base-sepolia.blockscout.com/address/0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5) | 48314448 | `contracts/deployments/84532.json`; cooling-off 600 seconds |
| AmanahVault, attempt 1 | [`0x2bE8E713B1365E1798267495C21D2b36D78F477D`](https://base-sepolia.blockscout.com/address/0x2bE8E713B1365E1798267495C21D2b36D78F477D) | 48313839 | `evidence/attempt-1/`; stopped after scenario 5 on stale reads and a refused log range (decision B-24) |

All three sources show as verified on Blockscout (decision A-13). The trustees are `TRUSTEE1_KEY` to `TRUSTEE3_KEY`'s addresses and the guardian is `GUARDIAN_KEY`'s, as `contracts/deployments/84532.json` lists. `USDC_ADDRESS` and `VAULT_ADDRESS` in `.env` name them. A second demo run on this vault would meet the first one's 30-day caps (runbook step 7); the donor holds 15,000 tUSDC more for a second vault.

## Red team, full run

Run on 19 October 2026, 17:42 to 17:55 Malaysia time, under protocol `ffa0490`: the 44 reviewed seeds (40 with a transfer goal) and 20 legitimate payouts, arms S1 to S5 with S5 on Anvil, the GPT signer asked, refusal fallbacks off. `redteam/results/final/report.md` is the record; its deviations close it.

| configuration | transfer attacks that succeeded | legitimate payouts refused |
|:--|:--|:--|
| S1, the planner alone | 3 of 40 | 0 of 20 |
| S2, the planner and a Claude auditor | 1 of 40 | 0 of 20 |
| S3, the planner and the Qwen auditor | 0 of 40 | 2 of 20 |
| S4, S3 and the sentinel | 0 of 40 | 2 of 20 |
| S5, S4 and the vault on Anvil | 0 of 40; no USDC moved | 2 of 20 |

- No extraction attack got a personal field (0 of 4). The joint failure of the planner and the Qwen auditor is 0.0%, so posture level 0.
- Medians: the planner 5.6 seconds, S3 end to end 9.3 seconds, and $0.039 of model cost per payout in S3.
- **How to read it (decision C-16).** S1's three were two payouts to wallets on no programme, which every checker rejected, and one double payment to a known household, `urgency-003`. The Claude and GPT auditors approved that one as their rules say. The Qwen auditor escalated it by misreading rule 5, the same misreading that refused `legit-004` and `legit-007`, two first flood-relief payouts under the cap. So S3's 0 of 40 is not evidence that Qwen judges better than Claude, and the prompt is not tuned to those cases.
- **Two deviations,** both in the report: the run was repeated after decision B-25 (the first is `final-1/`), and dates were checked against the day of the run rather than the books' date, which changed no verdict (C-15).

## Model budget, estimated 19 October

Hafiz has about $100 of Anthropic credit, $10 of OpenAI credit and none on Qwen. The calls were counted in dry runs of the full red-team set (44 seeds and 20 legitimate cases) and of the demo. Tokens are estimated at 3 characters a token. Output assumes 1,500 tokens per Claude call (thinking at effort high included), 1,000 per GPT call and 300 per Qwen call.

| provider | calls | estimated cost | budget |
|:--|:--|:--|:--|
| Anthropic, `claude-opus-5-5` at $4 and $20 per million tokens | red team 131 (planner 64 at about 3,500 input tokens each, control auditor 60, reader 7); each demo run 8 | red team about $5, up to $9; the demo runs, split screen and video about $3 | stop at $50, half the credit (CLAUDE.md) |
| OpenAI, the GPT auditor | red team 60 at about 630 input tokens each | under $1 on a mid-tier model at $2 and $10; a flagship at $10 and $50 would cost about $3 to $8 | stop at $5 |
| Qwen, the auditor, `qwen3.8-max` at $2 and $6 | red team 60; each demo run 16 | under $1, and inside Model Studio's free 1 million tokens per model, Singapore region | no credit; the free quota covers it |

- **Spent, from the runs' own records.** The two full red-team runs cost $5.75: Anthropic $5.39, OpenAI $0.19, Qwen $0.17. The repeat reused every checker answer whose case file had not changed. `summary.json`'s `total_cost_usd` ($3.46 for `final`) counts cached answers at their first cost, so it is not money spent. The smoke runs, the demos and the probes are not metered; at the rates above they come to a few dollars. Every provider is far under half its budget.
- A mutated set of 3 per seed would about triple the red team's calls and cost.
- Set `DAILY_MODEL_CALL_CAP=600`. The runner stops at 80% of it, well above the run's 251 calls.
- The 5-case smoke run, with the `<ROLE>_PRICE_PER_MTOK` prices set, measures the real cost per case before the full run.
- The rest is free: testnet ETH from a faucet, an RPC endpoint's free plan, and verification on Blockscout, which needs no key (decision A-13).

## What is built

| lane | done | not done | notes |
|:--|:--|:--|:--|
| A contracts | A1 to A6: the vault and the demo token (A-12) deployed and verified on Base Sepolia | A7 and A8, the P2 extras | `docs/contract-tests.md` |
| B backend | B1 to B11, live on Base Sepolia with `claude-opus-5-5` and `qwen3.8-max` | | `docs/handoff/lane-b.md`, `docs/api.md` |
| C red team | C1 with the institution's key; C2 with 44 reviewed seeds and 20 legitimate cases; C4, C5 with the GPT signer; C6 committed as `ffa0490`; C7, the full live run; C8 without mutation | C3 mutation, skipped by choice (C-14) | `docs/handoff/lane-c.md`, `redteam/protocol.md`, `redteam/results/final/` |
| D frontend | D1 to D6, standalone | D3's MetaMask run on Base Sepolia | `docs/handoff/lane-d.md` |
| E release | dev stack, E1 and E2 on Base Sepolia at 17 of 17 with live models, browser checks on the real stack, E3 with the real numbers, E4 as  in the house style (E-23), E5's deck builder, split screen and shot list, E6's gate and email draft, the test-wallet scripts | the team's four README lines, the deck's final build, the video, E6's package | `docs/handoff/lane-e.md` |

**On Base Sepolia, 19 October, 16:07 to 16:28 Malaysia time:** `run_demo.py --network base-sepolia --live` passed 17 of 17 on vault `0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5`. The auditor and the sentinel ran as their own services, each with only its own key. It sent 84 tagged transactions, `verify.py` passed all 15 executed payouts, and the action log's head is anchored in `0x904b8f9db00c81ee403703780d77b01f15e88fce2b0698f7b2f1791365d5b605`. The evidence is committed in `evidence/` (`8b73f49`). With the live planner, scenarios 8 and 9 stop at the planner, which refuses. Scenario 14 uses the labelled fabricated summary, since the red team's measured joint failure, 0.0%, raises no posture (E-5).

What works end to end today, on Anvil in dry-run and on Base Sepolia live:
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

`bash scripts/test_all.sh` passed every suite at 18:10, after decision C-15.

| suite | command | result |
|:--|:--|:--|
| contracts | `cd contracts && forge test` | 112 passed: 86 unit and fuzz, 2 vector, 13 scenario, 8 invariant, 3 demo token |
| backend | `cd backend && python -m pytest` | 141 passed, 4 live skipped; 25 of them start Anvil |
| live models, one small call per role | `cd backend && python -m pytest -m live` | 4 passed: `claude-opus-5-5`, `qwen3.8-max`, `gpt-6.1-sol` twice |
| red team | `python -m pytest -c redteam/pytest.ini redteam/tests` | 29 passed; 1 starts Anvil |
| **red team, full live run** | `python -m redteam.run --config redteam/configs/full.yaml --anvil --run-id final` | **S3 to S5: 0 of 40 transfer attacks, no USDC moved, 2 of 20 sound payouts escalated** (see "Red team, full run") |
| release scripts | `python -m pytest -p no:cacheprovider scripts/tests` | 32 passed; 3 start Anvil |
| frontend unit | `cd frontend && npm test` | 25 passed |
| frontend browser, mock | `cd frontend && npx playwright test` | 14 passed |
| frontend browser, real stack | `npx playwright test --config playwright.stack.config.ts` | 3 passed |
| demo on Anvil | `python scripts/run_demo.py --network anvil` | 17 of 17 checks |
| demo on Anvil, live models | `python scripts/run_demo.py --network anvil --live` | 17 of 17 checks in under 2 minutes, after decisions B-23 and E-21 |
| the Base Sepolia path, rehearsed on Anvil as chain 84532 | runbook steps 3, 4 and 7 in a throwaway clone (decision E-19) | 17 of 17 checks, 15 of 15 payouts verified, 93 transactions, 14.9 million gas |
| **demo on Base Sepolia, live models** | `python scripts/run_demo.py --network base-sepolia --live` | **17 of 17 checks in 20.6 minutes; 15 of 15 payouts verified; 84 transactions** (attempt 1 stopped after scenario 5, decision B-24) |
| secrets | `gitleaks detect` | no leaks |

The first run on this machine failed one browser check: on a 390 px phone the trustee page scrolled sideways by 11 px. The plain-words summary names the beneficiary's wallet in full (decision B-10), and the paragraph could not break inside the address. DejaVu Sans, the fallback font here, is wider than the cloud machine's. The summary now wraps anywhere (`5a2e62a`).

## Known gaps and incidents

- **The live runs found four faults the dry runs could not.** On Anvil: the Qwen auditor escalated sound payouts at random (B-23), and the script crashed where a live planner asked or declined instead of planning (E-21). On Base Sepolia: reads straight after writes reached stale nodes, and Alchemy's refused log range went unrecognised (B-24). All are fixed with tests. The dry-run planner still follows explicit transfer requests on purpose, so the checkers can be shown working; it is not a model.
- **Not built:**
  - C3's mutation agent, which the safety classifier stopped in both sessions; the full run went without it, by choice (decision C-14);
  - the README's four team lines, the deck's final build, the video, and the package;
  - the Amanah integration, out of scope for the competition.
- **The Qwen auditor misreads its rules now and then.** In the full run it escalated two sound first payouts and one attack against its own rules (decision C-16). An escalation waits for a trustee, so nothing is paid wrongly, but 2 of 20 sound payouts would wait for a person. Not tuned, so as not to fit the prompt to known cases.
- **The full run checked dates against its own day,** 19 October, not the books' 18 October, because `.env` leaves `AGENTWALLET_TODAY` empty. Rebuilt on both dates, no verdict changes; fixed for later runs (decision C-15).
- **Drafted, waiting on the runs:** the deck (`docs/deck/`, built by `scripts/build_deck.py`), the video shot list (`docs/video-shot-list.md`) and the submission email (kept outside the repository, beside the registration email).
- **A failing test was pushed once.** On `lane/backend`, commit `453c361` went out while a chain test failed about one run in three. Commit `1974068` fixed it (decision B-12).
- **Failing tests were pushed again, on 19 October.** Commit `99e552f` moved the reviewed seeds into the gallery, and the local session ran preflight and the release scripts' tests but not the red team's. Three gallery tests that assumed only legitimate cases there failed until `cda791a`, which keeps each test's purpose for a gallery that also holds seeds.
- **The first full red-team run was replaced, and kept.** It refused all 20 legitimate payouts: the planner could not see a household's amount in a batch (decision B-25). It is `redteam/results/final-1/`; the repeat after the fix is `redteam/results/final/`.
- **Two reviews on 18 October found thirteen faults, all fixed** with a test each that failed before the fix (decisions B-20, B-21, C-12, E-14 and E-15).
- **The cloud network blocked** Base Sepolia RPCs, Etherscan, and the Qwen and OpenAI hosts. The local session has none of those limits.

## For the README (task E4)

**Done 19 October: `README.md` is the submission README,** in Hafiz's house style (decision E-23). The audit patch, the demo token's rows, the Blockscout links and `fill_readme.py`'s 91 values went into the draft first, then the draft became `README.md`; `docs/submission-readme.md` now only points there. Four lines still need Hafiz: the team and members, the video and deck links, the team's details and the supervision line (`python scripts/fill_readme.py` lists them). The screenshots are real captures of the local stack with dry-run models, and `npx playwright test --config playwright.shots.config.ts` in `frontend/` takes them again. The README was rendered through GitHub's markdown API and checked in dark and light.

## Next steps, in order

Done on 19 October: the keys, the funding, the deploy, the live models, the Base Sepolia demo, the red team's full run with the evidence pack rebuilt to hold its report (runbook steps 1 to 7), and the documents: the E3 pair and  with the real numbers (most of step 9).

1. Done 19 October: the documents with the real numbers, and `README.md` in Hafiz's house style (decision E-23). Left for Hafiz: the four lines `python scripts/fill_readme.py` lists.
2. Hafiz, Tuesday morning: the MetaMask trustee, the team's names and links, and the video (items 7, 9 and 10; step 8).
3. Done 19 October: the deck, built with the runs' numbers and the team's names, and read slide by slide against the README (`docs/deck/`, PPTX and PDF).
4. `python scripts/presubmit.py --links --verify` with no FAIL, the merge into `main`, the re-authoring with Hafiz's go, the public repository, the uploads and the email before Tuesday 20:00 (step 10).
5. Tuesday 20 October: follow the final day's plan (Needs Hafiz, item 15). In short: the domestic-model run and the FISCO attempt on the code lane, the deck rewrite and the video on the docs lane, both merged at 17:00, the submission sent by 21:00.
