# Amanah: where to start

Amanah is an agent wallet for money held in trust: zakat, flood relief, bursaries. A payout moves only when three signers built to fail differently agree (a Claude planner, a Qwen auditor that never sees the chat, and a rules sentinel that sees only numbers), and the AmanahVault contract checks that the two models really come from different families, decides when a trustee must co-sign, and caps what machines can move in a day. The human stays the final decision-maker by mandate, not by clicking.

```text
hafiz@amanah-wallet:~$ cat ./SUBMISSION.md | head -3
344 attacks with live models: 0 of 312 payment attacks moved funds, and one model holding the key alone was fooled 13 times (the 300 drawn variants counted one by one; at seed level 0 of 40 moved, under 7.2%).
17 of 17 checks on Base Sepolia with live models, 84 real transactions, 15 of 15 payouts re-checked from the chain.
the same contract on FISCO BCOS (5 of 5), the same demo with no model from outside China (17 of 17).
```

**What no other agent wallet we know of does:** the contract itself refuses two AI signers of one model family ([on Base Sepolia](https://base-sepolia.blockscout.com/tx/0xcf1987e375d17a6b9ab8ed4fe574a8948e480716e448ccac8947ad2eea8cf0be)); the contract, not the app, decides when a person must sign, and its posture only tightens; the worst case is a number in code; the auditor never sees the chat; and the red team was registered before it ran. Each one with its proof, on the [README's first screen](README.md#hafizamanah-wallet-cat-in-one-minute).

### <samp>hafiz@amanah-wallet:~$ ls ./deliverables</samp>

| deliverable | where | what it is |
|:--|:--|:--|
| source code | this repository; [quick start](README.md#hafizamanah-wallet-bash-scriptsdev_upsh) | the vault (Solidity, Foundry), the three signer services and the API (Python, FastAPI), the app (React), the red team, and the scripts that reproduce every number. MIT licence. |
| demo video, 4 minutes 38 seconds | [watch in the browser](https://amanah-demo.vercel.app/amanah-demo.mp4); [in mainland China](https://hafizmnazman.github.io/amanah-wallet/amanah-demo-720p.mp4); [download, 1080p and 720p, with captions](https://github.com/hafizmnazman/amanah-wallet/releases/tag/v1.0.0) | two voices, Khaidhir attacking and Hafiz answering, over the app itself: an officer's batch with a question and a correction, five attacks refused (one in Chinese), an auditor taken down and the payout held until it is back, a trustee signing in MetaMask on Base Sepolia, the red team's numbers, `verify.py`, and the vault's `SameLineage` refusal on Blockscout. |
| pitch deck | [docs/deck/amanah-deck.pdf](docs/deck/amanah-deck.pdf) | the problem in the regulator's words, the design, the proof, the China path, the risks we know. |
| hosted demo | [amanah-demo.vercel.app](https://amanah-demo.vercel.app) | the app on recorded data in the browser, with no keys and no chain, and marked as mock data: try the attack chips on the Officer Desk. The live system is this repository and the vault on Base Sepolia. In mainland China, the same demo: [hafizmnazman.github.io/amanah-wallet](https://hafizmnazman.github.io/amanah-wallet/). |
| technical documentation | [docs/technical-documentation.md](docs/technical-documentation.md), [PDF](docs/technical-documentation.pdf) | how it is built, as a short paper: the architecture and what each signer sees, the contract and its loss bound, the red team, portability, reproduction. |
| security self-assessment | three pages: [PDF](docs/security-self-assessment-short.pdf), [Markdown](docs/security-self-assessment-short.md); in full: [docs/security-self-assessment.md](docs/security-self-assessment.md), [PDF](docs/security-self-assessment.pdf) | the short report covers the permission tiers, the four attacks with hallucination, leaked keys and privacy, the red team and the known risks. The full one adds the code and test behind every control, STRIDE, the OWASP Agentic and LLM Top 10, the PCAC convention, and a register of 28 known risks, each with an ID and a status (enforced, partial or accepted). |
| execution evidence | [evidence/](evidence/README.md); [README section 9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv) | 84 Base Sepolia transactions with hashes and explorer links, a trustee's MetaMask signature on an elevated payout ([evidence/sepolia-trustee/](evidence/sepolia-trustee/)), the hash-chained action log and its on-chain anchor, the Kimi run, the FISCO BCOS run, the ERC-8004 registrations, static analysis, and an evidence pack with a sha256 for every file. |
| claims register | [docs/claims.md](docs/claims.md) | every claim made anywhere, with where it is made, its evidence and the command that checks it: 66 rows. |
| the red team, as a benchmark | [redteam/README.md](redteam/README.md) | 44 attacks in 10 classes, 20 sound payouts, five architectures, a protocol committed before the run, and how to measure another wallet; then 300 code-made variants drawn at random with the hash of Base Sepolia block 48342456, mined at 07:40 on 20 October, after the addendum was pushed at 07:09 (`21307ca`). Its cost is measured too: in a companion run of 60 sound payouts the auditor escalated 14 (23.3%), all flood-relief grants that then wait for a person. |
| submission seal | `0x26c906db9c4cc59e7d4fad5f92148b288b7e396e76532d500da30f77fbe10fca`, in [Base Sepolia transaction 0xb8cabed4](https://base-sepolia.blockscout.com/tx/0xb8cabed4e39851364b5aa57f643bf45d3b1aac32d32f020e62f72e6b6a202df0) (block 48367324, 21:28 MYT on 20 October); the ten files and their hashes in [evidence/seal.json](evidence/seal.json) | the sha256 of every submitted file, written into one Base Sepolia transaction, so anyone can tell whether a file changed after the deadline. |

### <samp>hafiz@amanah-wallet:~$ cat ./rubric</samp>

| criterion | weight | what to look at | where |
|:--|:--|:--|:--|
| task completion | 40% | 16 scenarios with live models on Base Sepolia, 17 of 17 checks, 84 transactions; batch planning, clarification, correction, a trustee path signed in MetaMask on Base Sepolia, and a fail-closed queue | [README 3](README.md#hafizamanah-wallet-cat-walkthrough), [9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv); the video |
| security and compliance | 30% | a three-signer quorum the contract enforces; 0 of 312 payment attacks moved funds (40 registered, 272 drawn at random with a public block's hash); a worst case written in code (6,000 USDC a day, only to 45 approved households, until the mandates expire in October 2027); every control mapped to OWASP and to the PCAC convention, and a risk register with IDs and status | [README 6](README.md#hafizamanah-wallet-cat-quorum), [7](README.md#hafizamanah-wallet-cat-security); the security self-assessment |
| innovation and interaction | 30% | a quorum whose independence the contract checks, a tier the contract computes, a posture that only tightens on its own; a guide whose mood follows the wallet's state, and a trustee screen that never lets anyone sign blind | [README 4](README.md#hafizamanah-wallet-cat-contributions), [8](README.md#hafizamanah-wallet-cat-interaction), [thirty things](README.md#hafizamanah-wallet-cat-thirty-things) |
| challenge | bonus | the unchanged vault on FISCO BCOS; the three signers as ERC-8004 agents; the whole demo with no model from outside China; the attacks in Chinese | [README 9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv), [11](README.md#hafizamanah-wallet-cat-path-to-pilot) |

### <samp>hafiz@amanah-wallet:~$ cat ./ten-minutes</samp>

1. The [three-minute tour](README.md#hafizamanah-wallet-cat-tour): five stops, from the hosted demo to the hero revert on Blockscout, where the contract itself refused two signers of one model family.
2. The [first screen of the README](README.md#hafizamanah-wallet-cat-in-one-minute): the idea, the numbers and how to read them, variant level and seed level side by side.
3. [One message, two wallets](README.md#hafizamanah-wallet-python-scriptssplit_screenpy---live): the same rooftop message sent to a one-model wallet, which pays the attacker, and to Amanah, which does not.
4. [Thirty things Amanah does](README.md#hafizamanah-wallet-cat-thirty-things), each with the place to check it.
5. [Five commands, no keys needed](README.md#hafizamanah-wallet-cat-evidencetransactionscsv), at the end of the evidence section, then [verify every claim](README.md#hafizamanah-wallet-bash-scriptsreproducesh): ten commands and their real output, and [docs/claims.md](docs/claims.md) for the rest.
6. [The risk register](README.md#77-known-risks-and-limitations): what we have not solved, with an ID and a status each, said before anyone asks.

### <samp>hafiz@amanah-wallet:~$ bash scripts/reproduce.sh</samp>

```bash
git clone https://github.com/hafizmnazman/amanah-wallet && cd amanah-wallet
git submodule update --init --recursive
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
(cd frontend && npm ci)
bash scripts/reproduce.sh --fisco      # every suite, the demo, the reports from their rows, the app's numbers, FISCO BCOS
RPC_URL=https://sepolia.base.org VAULT_ADDRESS=0x558e8E8b2E20D41cE763A2c0FdC1d2c8A5B34FC5 \
  .venv/bin/python scripts/verify.py --csv evidence/transactions.csv     # 15 of 15 executed payouts pass
```

No model key is needed. On 20 October, after the history was re-authored, a fresh clone ran all of it in about eight minutes, the install included, and ended with `Everything reproduced.`

<sub>Team Amanah, Universiti Teknologi PETRONAS. MIT licence. Report a vulnerability as [SECURITY.md](SECURITY.md) describes.</sub>
