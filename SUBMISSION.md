# Amanah: where to start

Amanah is an agent wallet for money held in trust: zakat, flood relief, bursaries. A payout moves only when three signers built to fail differently agree (a Claude planner, a Qwen auditor that never sees the chat, and a rules sentinel that sees only numbers), and the AmanahVault contract checks that the two models really come from different families, decides when a trustee must co-sign, and caps what machines can move in a day. The human stays the final decision-maker by mandate, not by clicking.

```text
hafiz@amanah-wallet:~$ cat ./SUBMISSION.md | head -3
0 of 40 red-team payment attacks moved funds; one model holding the key signed 3 of 40. A random sample of 300 code-made variants, drawn after the plan was published, moved nothing either: 0 of 272.
17 of 17 checks on Base Sepolia with live models, 84 real transactions, 15 of 15 payouts re-checked from the chain.
the same contract on FISCO BCOS (5 of 5), the same demo with no model from outside China (17 of 17).
```

### <samp>hafiz@amanah-wallet:~$ ls ./deliverables</samp>

| deliverable | where | what it is |
|:--|:--|:--|
| source code | this repository; [quick start](README.md#hafizamanah-wallet-bash-scriptsdev_upsh) | the vault (Solidity, Foundry), the three signer services and the API (Python, FastAPI), the app (React), the red team, and the scripts that reproduce every number. MIT licence. |
| demo video, 4 minutes | [[fill: video link]] | an officer's batch with a clarification and a correction, two attacks refused, a trustee checking decoded fields before signing in MetaMask, the red-team page, `verify.py` on a live transaction. |
| pitch deck | [[fill: deck link]] | the problem in the regulator's words, the design, the proof, the China path, the risks we know. |
| hosted demo | [[fill: hosted demo URL]] | the app on mock data, marked as such: try the three attack chips on the officer desk. |
| technical documentation | [docs/technical-documentation.md](docs/technical-documentation.md), [PDF](docs/technical-documentation.pdf) | how it is built, as a short paper: the architecture and what each signer sees, the contract and its loss bound, the red team, portability, reproduction. |
| security self-assessment | three pages: [PDF](docs/security-self-assessment-short.pdf), [Markdown](docs/security-self-assessment-short.md); in full: [docs/security-self-assessment.md](docs/security-self-assessment.md), [PDF](docs/security-self-assessment.pdf) | the short report covers the permission tiers, the four attacks with hallucination, leaked keys and privacy, the red team and the known risks. The full one adds the code and test behind every control, STRIDE, the OWASP Agentic and LLM Top 10, the PCAC convention, and 26 known risks. |
| execution evidence | [evidence/](evidence/README.md); [README section 9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv) | 84 Base Sepolia transactions with hashes and explorer links, the hash-chained action log and its on-chain anchor, the Kimi run, the FISCO BCOS run, the ERC-8004 registrations, static analysis, and an evidence pack with a sha256 for every file. |
| claims register | [docs/claims.md](docs/claims.md) | every claim made anywhere, with where it is made, its evidence and the command that checks it: 53 rows. |
| the red team, as a benchmark | [redteam/README.md](redteam/README.md) | 44 attacks in 10 classes, 20 sound payouts, five architectures, a protocol committed before the run, and how to measure another wallet. |
| submission seal | [[fill: seal hash and transaction]] | the sha256 of every submitted file, written into one Base Sepolia transaction, so anyone can tell whether a file changed after the deadline. |

### <samp>hafiz@amanah-wallet:~$ cat ./rubric</samp>

| criterion | weight | what to look at | where |
|:--|:--|:--|:--|
| task completion | 40% | 16 scenarios with live models on Base Sepolia, 17 of 17 checks, 84 transactions; batch planning, clarification, correction, a trustee path and a fail-closed queue | [README 3](README.md#hafizamanah-wallet-cat-walkthrough), [9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv); the video |
| security and compliance | 30% | a three-signer quorum the contract enforces; 0 of 40 attacks moved funds; a worst case written in code (6,000 USDC a day, only to 45 approved households); every control mapped to OWASP and to the PCAC convention, and every known risk listed | [README 6](README.md#hafizamanah-wallet-cat-quorum), [7](README.md#hafizamanah-wallet-cat-security); the security self-assessment |
| innovation and interaction | 30% | a quorum whose independence the contract checks, a tier the contract computes, a posture that only tightens on its own; a guide whose mood follows the wallet's state, and a trustee screen that never lets anyone sign blind | [README 4](README.md#hafizamanah-wallet-cat-contributions), [8](README.md#hafizamanah-wallet-cat-interaction), [thirty things](README.md#hafizamanah-wallet-cat-thirty-things) |
| challenge | bonus | the unchanged vault on FISCO BCOS; the three signers as ERC-8004 agents; the whole demo with no model from outside China; the attacks in Chinese | [README 9](README.md#hafizamanah-wallet-cat-evidencetransactionscsv), [11](README.md#hafizamanah-wallet-cat-path-to-pilot) |

### <samp>hafiz@amanah-wallet:~$ cat ./ten-minutes</samp>

1. The [first screen of the README](README.md#hafizamanah-wallet-cat-in-one-minute): the idea, the numbers and how to read them.
2. [One message, two wallets](README.md#hafizamanah-wallet-python-scriptssplit_screenpy---live): the same rooftop message sent to a one-model wallet, which pays the attacker, and to Amanah, which does not.
3. [Thirty things Amanah does](README.md#hafizamanah-wallet-cat-thirty-things), each with the place to check it.
4. [Verify every claim](README.md#hafizamanah-wallet-bash-scriptsreproducesh): ten commands and their real output, then [docs/claims.md](docs/claims.md) for the rest.
5. [Known risks](README.md#77-known-risks-and-limitations): what we have not solved, said before anyone asks.

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

No model key is needed. On 20 October a fresh clone ran all of it in seven minutes and ended with `Everything reproduced.`

<sub>Team Amanah, Universiti Teknologi PETRONAS. MIT licence. Report a vulnerability as [SECURITY.md](SECURITY.md) describes.</sub>
