<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/readme/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/readme/banner-light.svg">
    <img src=".github/readme/banner-dark.svg" alt="AMANAH" width="850">
  </picture>
</div>

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/readme/card-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/readme/card-light.svg">
    <img src=".github/readme/card-dark.svg" alt="Amanah, an agent wallet for money held in trust and an entry for the 2026 Shenzhen FinTechathon: a payout on Base Sepolia needs a Claude planner, a Qwen auditor and a rules sentinel to agree, and the build is at the plan stage." width="850">
  </picture>
</div>

<p align="center">
  <a href="#hafizamanah-fintechathon-cat-plan"><img src="https://img.shields.io/badge/deadline-20_oct_2026_%C2%B7_23%3A59_myt-f08a5d?style=for-the-badge&labelColor=161b22" alt="deadline: 20 oct 2026, 23:59 myt"></a>
  <a href="#hafizamanah-fintechathon-tree-architecture"><img src="https://img.shields.io/badge/chain-base_sepolia_%C2%B7_testnet_usdc-8fcfc6?style=for-the-badge&labelColor=161b22" alt="chain: base sepolia, testnet usdc"></a>
  <a href="#hafizamanah-fintechathon-ls-docs"><img src="https://img.shields.io/badge/stage-plan_committed-3fb950?style=for-the-badge&labelColor=161b22" alt="stage: plan committed"></a>
</p>

```text
hafiz@amanah-fintechathon:~$ cat ./about
an agent wallet for money held in trust: zakat, flood relief, bursaries.
a payout moves only when three signers that fail differently agree, and a
contract on base sepolia checks them. an entry for the 2026 shenzhen
fintechathon, international track, topic f.

hafiz@amanah-fintechathon:~$ grep -cE '^\*\*[ZA-E][0-9]+\. ' IMPLEMENTATION_PLAN.md
43
```

### <samp>hafiz@amanah-fintechathon:~$ cat ./idea</samp>

Most agent wallets let one model read the attacker's text and hold the key. Amanah splits that power three ways and gives code the last word.

| signer | model | sees | signs when |
|:--|:--|:--|:--|
| planner | Claude | the officer's chat and the books | it has built the payout from the books |
| auditor | Qwen, a different model family | a case file of typed fields, never the chat | it answers approve |
| sentinel | rules and statistics, no model | numbers only | every rule passes |

The `AmanahVault` contract checks the three signatures against an on-chain registry and refuses a quorum whose two model signers come from the same family. It works out from on-chain facts when a human trustee must also sign, and it holds the caps, the allowlist and a pause switch. A red-team agent from a third model family attacks a sandbox copy every day, and it can only make the wallet stricter.

That is the design. None of it is built yet. The plan is.

### <samp>hafiz@amanah-fintechathon:~$ tree ./architecture</samp>

```text
contracts/   AmanahVault.sol, Foundry tests and invariants, deploy scripts   lane A
shared/      EIP-712 types and the contract ABI                             lane A
backend/     planner, auditor and sentinel services, chain client, API      lane B
redteam/     attack gallery, mutation agent, runner, protocol, results      lane C
frontend/    officer chat, plan cards, trustee signing, proof page          lane D
scripts/     dev_up.sh, run_demo.py, verify.py                              lanes Z, E
evidence/    action log, transactions csv, red-team report                  lane E
docs/        paths, borrowed code, technical documentation                  all
```

Every folder above is planned. Today only `docs/` and `.github/` exist.

### <samp>hafiz@amanah-fintechathon:~$ cat ./plan</samp>

The full plan, with a definition of done for each of its 43 tasks, is [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Every session, local or in the cloud, starts by reading [CLAUDE.md](CLAUDE.md), then [docs/PATHS.md](docs/PATHS.md) for how the plan maps onto this repository.

| lane | scope | branch | runs |
|:--|:--|:--|:--|
| Z | repository preparation | `main` | local, first |
| A | contracts | `lane/contracts` | cloud session |
| B | signers, planner, chain client, API | `lane/backend` | local |
| C | red team, immune loop, demo data | `lane/redteam` | cloud session |
| D | frontend | `lane/frontend` | local, from Monday |
| E | scripts, evidence, docs, deck, video | `lane/release` | local, Tuesday |

Lanes merge back into `main`: A first, then B, then C and D, then E. The deadline is Tuesday 20 October 2026, 23:59 Malaysia time (UTC+8).

### <samp>hafiz@amanah-fintechathon:~$ ls docs</samp>

| path | what |
|:--|:--|
| [CLAUDE.md](CLAUDE.md) | Rules for every session: lanes, commits, secrets, writing |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | The build plan: interfaces, lanes, tasks and the 16 demo scenarios |
| [docs/PATHS.md](docs/PATHS.md) | Where things are, and how the plan maps onto this repository |
| [docs/submission-readme.md](docs/submission-readme.md) | The README the judges will read, as a draft with `[[fill]]` markers. It replaces this page in lane E |
| [docs/borrowed.md](docs/borrowed.md) | Every piece of code copied from the Amanah final-year project, with the commit it came from |
| [.env.example](.env.example) | Every environment variable the build uses, with no values |

### <samp>hafiz@amanah-fintechathon:~$ cat ./borrowed</samp>

Amanah began as a final-year project at Universiti Teknologi PETRONAS: a multi-agent audit of zakat records, with a proof of every record kept on a permissioned chain. That repository stays private. When a task here needs one of its parts (the operating books, the rules engine, the integrity check, the spending cap), the code is copied in and listed in [docs/borrowed.md](docs/borrowed.md) with the commit it came from.

### <samp>hafiz@amanah-fintechathon:~$ cat ./not-chased</samp>

- **Hyperledger Fabric.** The final-year project keeps its proofs on Fabric. This entry runs on Base Sepolia, because Topic F asks for real public transaction hashes.
- **Real money and real people.** Testnet USDC only, and every beneficiary is invented.
- **Mainnet.** Nothing here goes to a chain where the money is real.
- **Bahasa Melayu.** The final-year project's app is bilingual. This entry is in English only, for the judges.

<sub>The banner and card are generated by <code>.github/readme/build.py</code> (standard library Python). Change a value at the top and run it again.</sub>
