# README audit

A line-by-line check of `docs/submission-readme.md` against what this repository holds on 18 October 2026, to prepare plan task E4. The README itself is not changed; Hafiz decides each item. Line numbers refer to the README on `lane/release` at the time of writing.

The README has 65 `[[fill` markers. 24 can be filled now from the repository, below. The rest need the Base Sepolia run, the red-team full run or a decision. Separately, 17 claims do not match what was built, or need rewording.

## Claims that do not match this repository

These need a decision before the README is final, because plan task E4 says to remove anything that did not ship.

| line | the README says | the repository has | suggestion |
|--:|:--|:--|:--|
| 51, 709 to 718 | backend 441 tests, evaluation 83, browser 186, chain gateway 5, chaincode 12 | Amanah's suites are not here. This repository has contracts 109, backend 119 (and 4 live), red team 24, frontend 23 unit, 14 browser checks on the mock and 3 on the real stack | Use this repository's numbers, unless the build moves into Amanah (handoff item 11) |
| 695, 696, 699 | top-level `auditor/`, `sentinel/` and `chaincode/` folders | the auditor and the sentinel are `backend/app/agentwallet/auditor/` and `sentinel/`; there is no `chaincode/` here; `shared/` holds the cross-lane interfaces | Replace the tree with the one below |
| 301, 698 | "installable PWA" and "Vite + React PWA" | a Vite and React app with no web manifest or service worker | Drop "PWA", or add a manifest |
| 324 to 350 | `setMandate` takes the mandate's fields one by one; `anchorDecision` takes a `uint8`; `tierOf` is `public` | `setMandate` takes a `Mandate` struct; `anchorDecision` takes a `Verdict` and returns the anchor id; `tierOf` is `external`; the excerpt also omits `setSignerActive`, `anchorReport` and `hashPayout` | Paste the corrected excerpt below |
| 467 | "nine classes", then a list of ten that includes multilingual variants and leaves out induced transfer | the case format's ten classes (`redteam/cases.py`, plan section 3.6) include `induced_transfer` and no multilingual class | Match the classes the final gallery has |
| 482 to 487 | a third lineage in the joint-failure matrix | five signers with `gpt_signer: true`: planner (Claude), Claude control auditor, Qwen auditor, GPT auditor and sentinel. The GPT auditor is a measurement and signs nothing (decisions B-14, C-10) | Name the third lineage GPT, and say it is measured, not a signer |
| 73, 497, 543, 728 | ERC-8004 records | not built (plan task A7 was a stretch) | Remove, as the markers themselves say |
| 621 | FISCO BCOS portability | not tested | Write "not yet tested", as the marker suggests |
| 652, 677 | `BASE_SEPOLIA_RPC_URL` | `RPC_URL`, in `.env.example` and every script | Rename in the README |
| 433 | "the backend checks the role on all 62 routes" | Amanah's route count. This API has 13 routes, and all but `/api/health` check the role (`roles.py`, `test_api.py::test_every_route_needs_a_role`) | Use this repository's count |
| 169, 433, 452 | an anonymised "how the fund was used" page for donors and the public | built after this audit began: `GET /api/usage` and the frontend's "Fund use" page, with totals by programme and month, no recipient and no wallet, and small months' sums hidden (decision B-15) | Keep the claim; mention the small-cell rule |
| 227, 316 | the books are "anchored on-chain", and checkers verify each record against its on-chain anchor | each record is checked against `redteam/data/books_anchor.json`, an off-chain file of sha256 hashes (decision B-2). What goes on-chain is the action log's head hash (`anchorReport`) and each refusal (`anchorDecision`) | Say "against its anchored hash", or anchor the anchor file's hash on-chain at setup |
| 53 | `verify.py` checks the "evidence anchor" of any payout | it checks the cited refusal anchor of an override, and roles, lineages, tier, limits, allowlist and trustee signatures for every payout. It does not check a routine payout's `evidenceHash` against an anchored record | Reword, or add that check |
| 295 | the Reporter is a reused language model | the trustee summary is a fixed template over the decoded EIP-712 fields (`reporter.py`), so nothing a model or a document says can reach it (decision B-10) | Say "a template over the decoded fields", which is the stronger claim |
| 294 | the sentinel uses rules and anomaly statistics | 8 deterministic rules on numbers (`sentinel/rules.py`); Amanah's anomaly statistics are not here | Say "8 deterministic rules", or port the statistics |
| 297 | operating books on FastAPI, 62 role-checked routes, five roles | a JSON file from lane C's generator (`redteam/data/books.json`) with a runtime ledger, and 4 roles from request headers (decisions B-1, B-2) | Describe the stand-in, or integrate Amanah's books |
| 193, 369 | a red-team agent mutates the gallery every day | the mutation agent (plan task C3) is not built, so a cycle runs the reviewed gallery and any mutated files already present | Keep only after C3 ships |

## Markers that can be filled now

| line | marker | value | source |
|--:|:--|:--|:--|
| 352 | keep the excerpt in sync | the corrected excerpt below | `contracts/src/IAmanahVault.sol` |
| 394 | invariant run count and depth | 8 invariants, 256 runs of 64 calls each, so each invariant is checked after every one of 16,384 calls | `contracts/foundry.toml`, `docs/contract-tests.md` |
| 400 | vault address | after A6 | `contracts/deployments/84532.json` |
| 532 | transcript | `docs/demo-transcript.md` | |
| 572 | confirm the command | `python scripts/run_demo.py --network base-sepolia`. It also checks every executed payout with `scripts/verify.py` and anchors the log's head hash | `scripts/run_demo.py` |
| 640 | confirm paths and commands | the corrected quick start below | |
| 645 | repository URL | `https://github.com/hafizmnazman/amanah-fintechathon` (private until plan task E6) | `git remote` |
| 661, 662 | start commands | in the corrected quick start below | `docs/api.md` |
| 689 | align with the tree | the corrected tree below | |
| 716 | contract unit and fuzz | 86 unit and fuzz tests, with 4 fuzz tests at 256 runs each; also 2 EIP-712 vector tests and 13 scenario tests | `docs/contract-tests.md` |
| 717 | contract invariants | 8 | |
| 718 | red-team cases | 20 legitimate now; the attack seeds and mutations come with plan tasks C2 and C3 | `redteam/gallery/` |
| 720 | one command | `bash scripts/test_all.sh` | `scripts/test_all.sh` |

## Markers that wait on a run or a decision

- **Team and licence (8, 736, 737, 751).** Hafiz.
- **Red-team numbers (10, 46 to 49, 465 to 489).** The full run, plan task C7. `redteam/results/final/report.md` has the tables in the README's shape. The protocol commit hash (465) comes with plan task C6.
- **Base Sepolia evidence (50, 55, 541, 547 to 562).** The demo run on Base Sepolia. Each table row's hash is in `evidence/transactions.csv`, tagged by scenario.
- **Scenario 7 (553).** It waits on decision A-10.
- **The model name in the log example (568).** It comes from `.env`, after the live run.
- **Pilot outreach (620).** Hafiz.
- **Video and links (16).** Plan task E5.

## Corrected contract excerpt (for section 6.2)

```solidity
enum Role { NONE, PLANNER, AUDITOR, SENTINEL, TRUSTEE, GUARDIAN, POSTURE_ORACLE }
enum Verdict { NONE, APPROVE, REJECT, ESCALATE }
struct Signer { Role role; bytes32 lineage; bytes32 evidenceView; bool active; }
struct Payout {
    bytes32 proposalId; bytes32 programmeId; address beneficiary;
    uint256 amount; bytes32 evidenceHash; uint256 nonce; uint256 deadline;
}
struct Mandate {
    uint256 cap; uint256 hardCeiling; uint256 dailyBudget; uint256 perBeneficiaryCap;
    uint64 expiry; bytes32 purposeHash; bool active;
}

function execute(Payout calldata p, bytes[] calldata sigs) external;              // routine or elevated quorum
function executeOverride(Payout calldata p, bytes32 refusalAnchor, bytes[] calldata sigs) external; // planner + two trustees, cites an anchored refusal
function tierOf(Payout calldata p) external view returns (uint8);                 // 1 routine, 2 elevated
function anchorDecision(bytes32 proposalId, Verdict verdict, bytes32 evidenceHash)
    external returns (bytes32 anchorId);                                           // PLANNER, AUDITOR or SENTINEL
function anchorReport(bytes32 reportHash) external;                               // POSTURE_ORACLE
function raisePosture(uint8 level, bytes32 reportHash) external;                  // POSTURE_ORACLE, upward only

// Governance: each call carries EIP-712 signatures from two distinct TRUSTEE keys
// over (action, paramsHash, govNonce, deadline), so old signatures cannot be replayed
function lowerPosture(uint8 level, uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;
function registerSigner(address key, Role role, bytes32 lineage, bytes32 evidenceView,
                        uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;
function setSignerActive(address key, bool active, uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;
function setMandate(bytes32 programmeId, Mandate calldata m,
                    uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;
function addBeneficiary(bytes32 programmeId, address wallet, bytes32 idHash,
                        uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external; // starts cooling-off
function unpause(uint256 govNonce, uint256 deadline, bytes[] calldata sigs) external;

function cancelBeneficiary(bytes32 programmeId, address wallet) external;        // one TRUSTEE or GUARDIAN, during cooling-off
function pause() external;                                                       // GUARDIAN
```

## Corrected quick start (for section 13)

```bash
git clone https://github.com/hafizmnazman/amanah-fintechathon amanah && cd amanah
git submodule update --init --recursive      # OpenZeppelin and forge-std
cp .env.example .env                         # fill in; never commit .env
python3 -m venv .venv && .venv/bin/pip install -r redteam/requirements.txt   # includes backend/requirements.txt

# Contracts
cd contracts && forge test                   # unit, fuzz, scenario and invariant tests
(set -a && . ../.env && set +a && forge script script/Deploy.s.sol --rpc-url base_sepolia --broadcast --verify)
cd ..                                        # the subshell keeps .env's keys out of this shell

# Everything on a local chain, in one command: Anvil, the auditor, the sentinel and the API
bash scripts/dev_up.sh

# Or each service by hand, each in its own shell with only its own key. Never export all of .env
# there. Each also needs the public settings: RPC_URL, VAULT_ADDRESS, CHAIN_ID and its model's.
cd backend
AUDITOR_KEY=... ../.venv/bin/uvicorn app.agentwallet.auditor.service:app --port 8101
SENTINEL_KEY=... ../.venv/bin/uvicorn app.agentwallet.sentinel.service:app --port 8102
PLANNER_KEY=... RELAYER_KEY=... ../.venv/bin/uvicorn app.main:app --port 8000
cd ..

# Frontend
cd frontend && npm ci && npm run dev && cd ..

# Scripted demo: writes evidence/action-log.jsonl and evidence/transactions.csv
.venv/bin/python scripts/run_demo.py --network base-sepolia

# Red-team suite
.venv/bin/python -m redteam.run --config redteam/configs/full.yaml --anvil

# Every test suite
bash scripts/test_all.sh
```

## Corrected tree (for section 14)

```text
amanah/
├── contracts/   AmanahVault.sol; unit, fuzz, scenario and invariant tests; deploy and fixture scripts
├── shared/      EIP-712 types, ABIs, test vectors and data formats shared by the lanes
├── backend/     agent wallet: planner, auditor and sentinel services, reader, chain client, API
├── redteam/     demo data, case format, runner, statistics, protocol, immune loop
├── frontend/    Vite + React app: chat, plan cards, trustee signing, proof and queue pages
├── scripts/     dev_up.sh, run_demo.py, verify.py, evidence_pack.py, test_all.sh
├── evidence/    action log, transactions CSV, demo summary, evidence pack
└── docs/        API, decisions, paths, demo transcript, handoffs, contract tests
```
