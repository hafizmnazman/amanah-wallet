# Claims register

Every claim Amanah makes, in the README, the technical documentation, the security self-assessment, the benchmark, the deck, the video or the submission letter, has a row here: what is claimed, where, the evidence, and the command that checks it. If a sentence is not in this table, it should not be in a document.

```text
hafiz@amanah-wallet:~$ grep -c "^| [A-H][0-9]" docs/claims.md
53
```

**Where it is made:** R is the README (with its section), T the [technical documentation](technical-documentation.md), S the [security self-assessment](security-self-assessment.md), B the [benchmark](../redteam/README.md), D the deck, V the video, L the submission letter and A the app. **Checks** name a command in [the commands](#the-commands) below. Run them from the repository root, after the [quick start](../README.md#hafizamanah-wallet-bash-scriptsdev_upsh)'s install. No check needs a model key; the chain checks need only a public Base Sepolia endpoint.

### A. The red team

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| A1 | No payment attack moved funds through Amanah: 0 of 40 | R first screen, summary, badge; T; S; B; D; V; L | `moved_funds` in [`final/summary.json`](../redteam/results/final/summary.json); the S5 row of [the report](../redteam/results/final/report.md) | K1; `show redteam/results/final/summary.json moved_funds` |
| A2 | One model holding the key signed 3 of 40 (7.5%, 95% CI 2.6 to 19.9) | R; T; S; B; D; V | `attack_success_transfer` S1 in the same file | `show redteam/results/final/summary.json attack_success_transfer S1` |
| A3 | 0 against 3 is not significant on its own: exact McNemar p = 0.25, 0.75 after Holm | R first screen, 7.7; T; S; B; D | `mcnemar` in the same file | `show redteam/results/final/summary.json mcnemar "S1 vs S3"` |
| A4 | Over all 44 attacks: 3 of 44 for one model, 0 of 44 for the quorum (95% CI 0.0 to 8.0) | R summary, 7.5 | `attack_success` in the same file | `show redteam/results/final/summary.json attack_success S3` |
| A5 | Sound payouts held back: 0 of 20 for one model, 2 of 20 with the Qwen auditor; both waited for a trustee | R summary, 7.5; S; B | `false_refusal` in the same file; decision C-16 | `show redteam/results/final/summary.json false_refusal` |
| A6 | The planner and the Qwen auditor never failed together on a payment attack (0.0%) | R 4.1, 7.5; T; S; B | `joint_failure_matrix` in the same file | `show redteam/results/final/summary.json joint_failure_matrix planner auditor_qwen` prints `0.0` |
| A7 | The Qwen and GPT auditors, different families reading the same case file, failed together on every attack that fooled Qwen | R 4.1; T | the same matrix: Qwen alone 0.075, Qwen with GPT 0.075 | `show redteam/results/final/summary.json joint_failure_matrix auditor_qwen` |
| A8 | The quorum costs US$0.0389 and 9.3 s a payout (median), against US$0.0365 and 5.6 s for one model | R first screen, 7.5; T; B; D | `median_cost_usd_by_arm`, `median_latency_ms_by_arm` | `show redteam/results/final/summary.json median_cost_usd_by_arm` |
| A9 | The protocol was committed before the run: `ffa0490` at 17:11 on 19 October, before the first full run began at 17:15 | R 7.5, thirty things 8; S; B | the git history; `started_at` in [`final-1/manifest.json`](../redteam/results/final-1/manifest.json) | `git log --format="%h %ci %s" -- redteam/protocol.md`; `show redteam/results/final-1/manifest.json started_at` |
| A10 | The repeat after the fix reused 37 of each auditor's 60 verdicts from the first run, and asked the planner again every time | B; S; the final report's deviations | the `cached` field in [`final/results.jsonl`](../redteam/results/final/results.jsonl) | K11 |
| A11 | Every attack that fooled a planner alone came from two classes, urgency and induced transfer | B; S | the per-class tables of the final and Kimi reports | read "Attack success by class" in each report |
| A12 | The auditor's prompt was not tuned to the run, and all three runs used the same prompts: planner `5af98864ad7a6cfa`, reader `be774090dc9a2081`, auditor `86fbba0d4b0e3ba4` | R 7.5; S; B | `prompt_fingerprints` in each run's `manifest.json`; decision C-16 | `show redteam/results/final/manifest.json prompt_fingerprints`, and the same for `domestic-kimi` and `zh-kimi` |

### B. Base Sepolia

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| B1 | 16 scenarios with live models passed 17 of 17 checks, in 84 real transactions | R first screen, 9, badge, card; T; S; D; V; L | [`evidence/demo-summary.json`](../evidence/demo-summary.json), [`evidence/transactions.csv`](../evidence/transactions.csv) | `show frontend/src/data/facts.json base_sepolia`; K1 shows that file is what the evidence gives |
| B2 | Every executed payout re-checks from the chain alone: 15 of 15 | R about, first screen, thirty things 11; S; L | [`scripts/verify.py`](../scripts/verify.py) | K2 |
| B3 | A routine payout was paid on three machine signatures, with no human | R summary, 9 | scenario 6, [`0xf0f4...4dba`](https://base-sepolia.blockscout.com/tx/0xf0f40271383e44fe9adc9bafc1e96689deeeb5ceb7178faf7ea765f6d62a4dba) | K3 on that hash: tier 1, three signers |
| B4 | Three machine signatures to a wallet two trustees never approved reverted (`NotAllowlisted`) | R thirty things 5, 7.2, 9; S | scenario 10, [`0xb06b...0588`](https://base-sepolia.blockscout.com/tx/0xb06b492221b40d2df0523f5bdffc6b5df0d31912859e9d577116b8b514000588) | K4 on that hash prints `false` |
| B5 | Two Claude keys as planner and auditor reverted (`SameLineage`) | R 4.1, thirty things 1, 9; S | scenario 11, [`0xcf19...f0be`](https://base-sepolia.blockscout.com/tx/0xcf1987e375d17a6b9ab8ed4fe574a8948e480716e448ccac8947ad2eea8cf0be) | K4 on that hash; K7 `test_scenario11_sameLineageQuorumReverts` |
| B6 | The planner key cannot add a beneficiary (`NotTrustee`) | R 7.2, 9; S | scenario 12, [`0x1e69...6ae9`](https://base-sepolia.blockscout.com/tx/0x1e6919b0c61b94d94d57d14fdb2965743e583f7ac88ac72430579539f9bb6ae9) | K4 on that hash; K7 `test_addBeneficiary_byPlannerReverts` |
| B7 | An override cites an anchored refusal: the auditor's refusal anchored, then planner and two trustees paid | R 6.3, 9, thirty things 21; S | scenario 15, anchor [`0x60e5...9ae1`](https://base-sepolia.blockscout.com/tx/0x60e57767154c4c9019d299bd63350a0bf4b0c91f3d3ff9cfbbf51909371b9ae1), override [`0x01ac...edd9`](https://base-sepolia.blockscout.com/tx/0x01ac84e4071d24b6f4f54d54d1eafe27ed95731cdfb8a45ce35a164ade29edd9) | K3 on the override hash checks the cited refusal |
| B8 | The action log is hash-chained, and its head is anchored on-chain | R 9, thirty things 24; S | [`evidence/action-log.jsonl`](../evidence/action-log.jsonl); head anchor [`0x904b...b605`](https://base-sepolia.blockscout.com/tx/0x904b8f9db00c81ee403703780d77b01f15e88fce2b0698f7b2f1791365d5b605) | `show evidence/demo-summary.json log_verified` prints `True`; `test_an_edited_record_breaks_verification` |
| B9 | The vault and the token have verified source on Blockscout, and the deployer holds no role | R 9, 6.2; S | [the vault on Blockscout](https://base-sepolia.blockscout.com/address/0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5) | K7 `test_constructor_deployerHoldsNoRole` |

### C. The contract

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| C1 | The vault refuses a quorum whose planner and auditor share a family, even with trustees signing | R 4.1, 6.2; T; S | `SameLineage` in [`AmanahVault.sol`](../contracts/src/AmanahVault.sol) | K7 `test_execute_sameLineageRevertsEvenWithTrustees` |
| C2 | The vault computes the tier itself from the amount, the day's spend and the posture; no agent chooses it | R 4.2, 6.3; T; S | `tierOf` | K7 `test_tierOf_capBoundary`, `test_eightyPercentLine_flipsTier`, `testFuzz_tierOf_matchesModel` |
| C3 | The hard ceiling, the daily budget and each household's 30-day cap revert in every tier, overrides included | R 4.2, 6.3; S | `tierOf` reverts before it returns a tier | K7 `test_override_respectsTheBeneficiaryCap`, `test_override_mayExceedTheCapButNotTheHardCeiling` |
| C4 | With every machine key stolen and no trustee key, at most 6,000 USDC a day moves, only to the 45 households two trustees approved | R first screen, 6.5, thirty things 4; T; S; D; V | the `worst_case` block of [`facts.json`](../frontend/src/data/facts.json), from the mandates; `invariant_machineBound`, `invariant_onlyAllowlisted` | `show frontend/src/data/facts.json worst_case`; K6 |
| C5 | With one trustee key stolen as well, the ceiling is the full daily budgets, 7,500 USDC a day, still only to approved households | R 6.5; S | the daily budgets in [`redteam/data/mandates.json`](../redteam/data/mandates.json): 2,500, 3,000 and 2,000 | `show redteam/data/mandates.json` |
| C6 | Eight invariants held after each of 16,384 random calls | R 6.5, thirty things 7; T; S | [`contracts/test/Invariant.t.sol`](../contracts/test/Invariant.t.sol) | K6 |
| C7 | Each of 12 deliberately planted bugs made tests fail | R 6.5, thirty things 7; T; S | [`docs/contract-tests.md`](contract-tests.md), the planted-bug table | follow its steps: plant one, run `forge test` |
| C8 | Every branch and every function of the vault is covered (lines 97.9%) | R first screen, thirty things 25; S | [`docs/static-analysis.md`](static-analysis.md) | K8 |
| C9 | Slither finds 11 results: no high, one medium that is a false positive, six low, four informational | R thirty things 25; S | [`evidence/static-analysis/slither.json`](../evidence/static-analysis/slither.json); the triage in `static-analysis.md` | K9 |
| C10 | The posture rises by itself and falls only with two trustees | R 4.3, 6.4, thirty things 14; T; S | `raisePosture`, `lowerPosture`; scenario 14 | K7 `test_raisePosture_onlyUpwards`, `test_lowerPosture_oracleCannotSign`; K6 `invariant_postureMonotone` |
| C11 | A new beneficiary waits out a cooling-off that one trustee or the guardian can cancel | R 4.4, thirty things 22; S | `cancelBeneficiary` | K7 `test_cancelBeneficiary_duringCoolingOff`, `test_cancelBeneficiary_onlyTrusteeOrGuardian` |
| C12 | A checker's refusal is anchored on-chain by its own key, and an override can cite it only once | R thirty things 21; S | `anchorDecision`, `executeOverride` | K7 `test_override_refusalCanBeCitedOnce`; `test_checker_anchors_its_own_refusal` |

### D. The agents and the app

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| D1 | Each signer sees a different slice of the evidence: the chat and the books, a typed case file, numbers only | R 6.1, thirty things 2; T; S | `auditor/casefile.py`, `sentinel/rules.py` | `test_case_file_has_no_personal_data_notes_or_reasons`, `test_features_are_numbers_only` (K10) |
| D2 | Untrusted documents reach the planner only as typed fields from a reader with no tools | R 7.2, thirty things 13; S | [`reader.py`](../backend/app/agentwallet/reader.py); scenario 9 | `test_fields_are_typed_and_advisory`, `test_injection_fixtures_set_the_flag` (K10) |
| D3 | A trustee never signs blind: Sign stays disabled until the typed data decodes and the summary matches it | R 7.2, thirty things 12; S; V | `safe` in [`PendingPayoutCard.tsx`](../frontend/src/components/trustee/PendingPayoutCard.tsx); [`summaryCheck.ts`](../frontend/src/lib/summaryCheck.ts) | `cd frontend && npm test`; `frontend/e2e/trustee.spec.ts` |
| D4 | It fails closed: with a checker or the chain down, payouts queue and a trustee is alerted | R 7.2, 8, thirty things 20; S | [`queue.py`](../backend/app/agentwallet/queue.py) | `test_fail_closed_then_drained`, `test_without_a_chain_confirm_fails_closed_to_the_queue` (K10) |
| D5 | No personal data enters a model's context or the chain, and the public page hides the sum of any month with fewer than three payouts | R 7.3, thirty things 23; S | `MIN_CELL = 3` in [`usage.py`](../backend/app/agentwallet/usage.py) | `test_planner_summary_holds_no_personal_data`, `test_no_total_gives_a_small_month_away` (K10) |
| D6 | 12 of the API's 14 routes check the caller's role; the other two hold no personal data | R rubric map, 7.2; S | `api.py`; [`docs/api.md`](api.md) | `test_every_route_needs_a_role`, `test_the_report_is_public` (K10) |
| D7 | Anyone can try to trick it in one click: three attack chips on the officer desk | R thirty things 29; A; V | `TRY_TRICKS` in [`ChatPanel.tsx`](../frontend/src/components/chat/ChatPanel.tsx) | the hosted demo |
| D8 | The app states no number by hand: its facts are generated from the run files | R thirty things 28; T | [`scripts/export_ui_data.py`](../scripts/export_ui_data.py) | K1, the facts line |

### E. Beyond one chain and one vendor

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| E1 | The whole demo runs with no model from outside China: Kimi K3 plans, Qwen audits, 17 of 17 checks | R first screen, 9, 11, thirty things 15; T; S; D; V; L | [`evidence/domestic-anvil/`](../evidence/domestic-anvil/); decision E-30 | `show frontend/src/data/facts.json portability domestic checks_passed` |
| E2 | With Kimi planning, 0 of 40 payment attacks moved funds; Kimi alone was fooled by 5 of 40 | R 7.5, 7.7; S; B | [`domestic-kimi/summary.json`](../redteam/results/domestic-kimi/summary.json) | K1 re-renders the report; `show redteam/results/domestic-kimi/summary.json attack_success_transfer` |
| E3 | When every model and rule said yes to `urgency-003`, the contract still asked a person (tier 2) | R thirty things 6, 7.5; S; B; D | the `urgency-003` row of [`domestic-kimi/results.jsonl`](../redteam/results/domestic-kimi/results.jsonl) | K12 |
| E4 | The same attacks in Chinese came out exactly as in English: 10 of 10, none moved | R first screen, 7.5, 9, thirty things 16; S; B | [`zh-kimi/`](../redteam/results/zh-kimi/report.md); decision E-34 | K1; `show frontend/src/data/facts.json portability chinese_attacks` |
| E5 | The unchanged vault runs on FISCO BCOS 3.17.1: 56 of 56 setup transactions, 5 of 5 checks, by two settings and no code change | R first screen, 9, 11, thirty things 17; T; S; D; V; L | [`evidence/fisco/summary.json`](../evidence/fisco/summary.json); decision E-31 | K13 |
| E6 | The three machine signers are ERC-8004 agents 10302, 10303 and 10304, each bound to the key the vault counts by that key's own signature | R first screen, 6.7, 9, thirty things 18; T; S; L | [`evidence/erc8004.json`](../evidence/erc8004.json); decision E-32 | K5 |

### F. Engineering

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| F1 | 366 tests run on every push, with dry-run models and no secrets | R first screen, 15, card, thirty things 26; S; D | [`scripts/test_all.sh`](../scripts/test_all.sh); [the workflow](../.github/workflows/tests.yml) | K1 |
| F2 | One command reproduces the published numbers, and the three reports render from their rows byte for byte | R verify, thirty things 27; T; B | [`scripts/reproduce.sh`](../scripts/reproduce.sh) | K1 |
| F3 | The red team is released as a benchmark that others can run | R thirty things 30; B | [`redteam/README.md`](../redteam/README.md) | its smoke run needs no key |

### G. Comparisons and firsts

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| G1 | To our knowledge, no other agent wallet requires co-signatures from different model lineages and enforces it in the contract; AI co-signing itself is not new | R 4, 10; T; S; D; V; L | the linked documentation in README section 10 (Coinbase, Privy, Turnkey, Safe, Newton, Nava, Lit, Blockaid, MetaMask, Don't Get Drained), as of October 2026 | read the linked pages |
| G2 | To our knowledge, the first pre-registered red team of an agent wallet that publishes per-signer joint failure | B | the protocol and the matrix (A6, A9) | the same |

### H. From the research project

| # | claim | made in | evidence | check |
|:--|:--|:--|:--|:--|
| H1 | With all AI switched off, rules and statistics alone scored F1 0.706, against 0.712 with the agents; the audit agents' prompts are fingerprinted `ec02406645ee3f2c` | R 12 | the final-year project's evaluation harness, which is not in this repository | none here: this register cannot check it, and we say so |

### The commands

Set a public endpoint once for the chain checks, and a helper that reads one value out of a JSON file:

```bash
export RPC_URL=https://sepolia.base.org VAULT_ADDRESS=0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5
show() { python -c "import json,sys; from functools import reduce; print(reduce(lambda d,k: d[k], sys.argv[2:], json.load(open(sys.argv[1]))))" "$@"; }
```

| id | command | expected |
|:--|:--|:--|
| K1 | `bash scripts/reproduce.sh` | one `pass` line per suite, the demo's `17 of 17 checks as expected`, `pass` for each of the three reports and for `facts.json`, then `Everything reproduced.` |
| K2 | `python scripts/verify.py --csv evidence/transactions.csv` | `15 of 15 executed payouts pass` |
| K3 | `python scripts/verify.py <txHash>` | `<txHash>: PASS`, then a `pass` line for each check: signers, lineages, tier, caps, budget, allowlist, cooling-off, and an override's cited refusal |
| K4 | `cast receipt <txHash> status --rpc-url "$RPC_URL"` | `false` for a reverted transaction; Blockscout shows the error name |
| K5 | `python scripts/register_agents.py --check` | three `[pass]` lines, one per agent |
| K6 | `cd contracts && forge test --match-contract Invariant` | `8 tests passed`, each with `runs: 256, calls: 16384` |
| K7 | `cd contracts && forge test --match-test <name>` | `[PASS] <name>` |
| K8 | `cd contracts && forge coverage --report summary --ir-minimum` | the `src/AmanahVault.sol` row: `97.89% (186/190)`, `98.40% (246/250)`, `100.00% (53/53)`, `100.00% (33/33)` |
| K9 | `cd contracts && uvx --from "slither-analyzer==0.11.6" slither . --filter-paths "lib/\|test/\|script/" --exclude-dependencies` | `11 result(s) found` |
| K10 | `cd backend && python -m pytest -q -k <name>` | the named tests pass |
| K11 | `python -c "import json; rows=[json.loads(l) for l in open('redteam/results/final/results.jsonl')]; print(sum(bool(r['checkers'].get('auditor_qwen', {}).get('cached')) for r in rows))"` | `37` |
| K12 | `python -c "import json; r=[json.loads(l) for l in open('redteam/results/domestic-kimi/results.jsonl') if 'urgency-003' in l][0]; print(r['success'])"` | `True` for S3 and S4, `False` for S5 |
| K13 | `bash scripts/reproduce.sh --fisco` | `5 of 5 checks as expected on FISCO-BCOS-Web3RPC/3.17.1-Release/...` |

### External facts

Facts about the world that the documents cite, each with its source. These are not ours to check by command; the link is the evidence.

| fact | made in | source |
|:--|:--|:--|
| Alipay's AI Pay passed 100 million users in February 2026 | R 1 | [FinTech Global](https://fintech.global/2026/04/23/alipay-expands-ai-pay-to-openclaw-type-agents/) |
| A Morse-encoded message made Bankrbot send about US$150K to 200K in May 2026 | R 1; D | [Giskard](https://giskard.ai/knowledge/how-grok-got-prompt-injected-an-x-user-drained-150-000-from-an-ai-wallet), [OECD](https://oecd.ai/en/incidents/2026-05-04-4a73) |
| With no spending limit, 4 of 26 LLMs paid hidden payment instructions on live websites | R 1 | [Zscaler](https://www.zscaler.com/blogs/security-research/indirect-prompt-injection-web-content-targets-ai-agents) |
| Bybit's signers approved a malicious payload while the interface showed the right address | R 1 | [FBI](https://www.ic3.gov/PSA/2025/PSA250226), [NCC Group](https://www.nccgroup.com/research/in-depth-technical-analysis-of-the-bybit-hack/) |
| Two wrong models choose the same wrong answer about 60% of the time | R 1 | [ICML 2025](https://proceedings.mlr.press/v267/kim25e.html) |
| Organisations lose about 5% of revenue to fraud; missing controls appear in 32% of cases | R 2 | [ACFE 2024](https://anchin.com/wp-content/uploads/2024/08/2024-ACFE-Occupational-Fraud-Report.pdf) |
| The PCAC's August 2026 convention asks for authorisation boundaries, limits, Know Your Agent, security testing and human fallback | R 2, 7.6; S | [Xinhua](https://www.news.cn/fortune/20260824/b44c884bab5d4f89bce4262c362b0736/c.html), [Yicai](https://www.yicaiglobal.com/news/chinas-payment-clearing-association-issues-pact-to-prevent-risks-from-agentic-payments) |
| PBoC Deputy Governor Lu Lei: payment governance is "built around humans as the final decision-makers" | R 2 | [Phemex News](https://phemex.com/news/article/pboc-official-warns-agent-payments-must-not-blur-liability-lines-95008) |
| WeBank's direction: from "humans execute, AI assists" to "AI executes by default, humans handle only exceptions" | R 2; D | [Jiemian](https://www.jiemian.com/article/14835776.html) |
| AP2's autonomous mode: the user approves constraints once, and the agent signs each closed mandate with its own key | R 6.3, 6.7; T | [AP2 specification](https://ap2-protocol.org/ap2/specification/) |
| The IMF names homogeneous models across agents as a source of correlated risk | R 7.6; T | [IMF Note, April 2026](https://www.imf.org/en/publications/imf-notes/issues/2026/04/22/how-agentic-ai-will-reshape-payments-575560) |
| The FSB's 15 October 2026 practices ask for records that let agentic actions be reconstructed | R 7.6 | [FSB](https://www.fsb.org/2026/10/fsb-finalises-sound-practices-for-the-responsible-adoption-of-artificial-intelligence-ai/) |
| The NFRA's June 2026 guidance asks for human intervention at key links of high-risk AI uses | R 7.6 | [Xinhua](https://www.news.cn/tech/20260618/52e251c6c92a4059bae3936266172a6e/c.html) |
| The PBoC already uses e-CNY smart contracts for government subsidies | R 11; D | [Forkast](https://forkast.news/china-to-speed-up-expand-digital-yuan-smart-contracts-pboc-official-says/) |
| Knight and Leveson (1986): independently written versions still fail together on the same hard inputs | R 4.1; T; D | [IEEE TSE](https://doi.org/10.1109/TSE.1986.6312924) |
| Nava raised US$8.3M in April 2026 for a verifier that holds funds in escrow until a transaction matches intent | R 10 | [Fortune](https://www.fortune.com/2026/04/14/nava-seed-funding-ai-financial-agents/) |
