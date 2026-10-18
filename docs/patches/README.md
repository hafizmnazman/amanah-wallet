# Patches waiting on a decision

Each patch here is a change that is ready, tested, and waiting for Hafiz to decide. Apply one with `git apply`, then commit it as usual. Each was made against the `lane/release` commit named below. If the files have changed since, `git apply --3way` merges what it can.

| patch | decision | made against | what it does | checked |
|:--|:--|:--|:--|:--|
| `a10-flood-cap-1500.patch` | A-10, option 1 (recommended) | `4393c26` | Raises the flood relief per-beneficiary cap from 600 to 1,500 USDC and regenerates the data. It moves one chain test's over-cap amount to 1,501 and records the decision in `docs/decisions.md`, `shared/fixture-data.md` and `docs/demo-transcript.md` | at `4393c26`, and again at `9acfa2c` after decision B-17: contracts 109, backend 115, red team 23; `run_demo.py --network anvil` 17 of 17 |
| `readme-e4-fills.patch` | E4: accept the README audit's fixes | `6e1b968` | Applies `docs/readme-audit.md` to `docs/submission-readme.md`: 31 edits. It fills the 24 markers the repository can answer (113 markers become 89) and replaces Amanah's test counts with this repository's. It corrects the contract excerpt, the quick start and the tree, and removes ERC-8004. It rewords the reporter, sentinel, books, PWA and on-chain anchor claims | no dashes; the test counts are those of the merge of decision B-18; the remaining markers wait on the Base Sepolia run, the red-team run or Hafiz |
| `licence-mit.patch` | E6: the project licence | `cd4592d` | Adds an MIT `LICENSE`, copyright "The Amanah authors". Every Solidity file already declares `SPDX-License-Identifier: MIT`, and the README's dependencies are MIT or Apache-2.0. Then set the README's "Project licence" line to "MIT, see LICENSE" | `git apply --check` passes; `scripts/presubmit.py`'s licence check passes once it is committed |

```bash
git apply docs/patches/readme-e4-fills.patch      # read it first: it rewrites parts of the README
git commit -am "Apply the README audit's fixes"
git apply docs/patches/a10-flood-cap-1500.patch
git commit -am "Raise the flood relief per-beneficiary cap to 1,500 USDC (decision A-10)"
git apply --index docs/patches/licence-mit.patch  # --index stages the new LICENSE file
git commit -m "License the project under MIT"
```

Option 2 of A-10, a smaller grant, has no patch. It would change `REQ-REL-0001`'s amount in `redteam/datagen.py` to between 301 and 600 USDC, and the 1,200 in `docs/demo-transcript.md` and the frontend mock.
