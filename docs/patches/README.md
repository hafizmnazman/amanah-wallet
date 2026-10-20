# Patches waiting on a decision

Each patch here is a change that is ready, tested, and waiting for Hafiz to decide. Apply one with `git apply`, then commit it as usual. Each was made against the `lane/release` commit named below. If the files have changed since, `git apply --3way` merges what it can.

| patch | decision | made against | what it does | checked | status |
|:--|:--|:--|:--|:--|:--|
| `a10-flood-cap-1500.patch` | A-10, option 1 (recommended) | `f62eb90` | Raises the flood relief per-beneficiary cap from 600 to 1,500 USDC and regenerates the data. It moves one chain test's over-cap amount to 1,501 and records the decision in `docs/decisions.md`, `shared/fixture-data.md` and `docs/demo-transcript.md` | at `f62eb90`, and again at `f121dad` after decision B-17: contracts 109, backend 115, red team 23; `run_demo.py --network anvil` 17 of 17 | applied in `5715603` on 19 October; the Anvil demo then gave 17 of 17 |
| `readme-e4-fills.patch` | E4: accept the README audit's fixes | `31ec2a7` | Applies `docs/readme-audit.md` to `docs/submission-readme.md`: 31 edits. It fills the 24 markers the repository can answer (113 markers become 89) and replaces Amanah's test counts with this repository's. It corrects the contract excerpt, the quick start and the tree, and removes ERC-8004. It rewords the reporter, sentinel, books, PWA and on-chain anchor claims | no dashes; the test counts are those of the merge of decision B-18; the remaining markers wait on the Base Sepolia run, the red-team run or Hafiz | waiting; runbook step 8. After it, the README's USDC rows need the demo token (decision A-12) |
| `licence-mit.patch` | E6: the project licence | `55d4f8c` | Adds an MIT `LICENSE`, copyright "The Amanah authors". Every Solidity file already declares `SPDX-License-Identifier: MIT`, and the README's dependencies are MIT or Apache-2.0. Then set the README's "Project licence" line to "MIT, see LICENSE" | `git apply --check` passes; `scripts/presubmit.py`'s licence check passes once it is committed | applied in `d43a74e` on 19 October; the README's licence line comes with step 8 |

```bash
git apply docs/patches/readme-e4-fills.patch      # read it first: it rewrites parts of the README
git commit -am "Apply the README audit's fixes"
```

Option 2 of A-10, a smaller grant, was not chosen.
