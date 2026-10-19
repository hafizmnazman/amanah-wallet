# Contributing

Amanah is a research prototype built by Team Amanah at Universiti Teknologi PETRONAS. Issues and pull requests are welcome. A security problem goes through [SECURITY.md](SECURITY.md), never a public issue.

### <samp>hafiz@amanah-wallet:~$ bash scripts/test_all.sh</samp>

Set up as the README's [quick start](README.md#hafizamanah-wallet-bash-scriptsdev_upsh) says, then run every suite before a pull request. It needs no model key: every role answers in dry-run without one.

```bash
bash scripts/test_all.sh          # every suite and the 16 scenarios on a fresh Anvil, about three minutes
bash scripts/reproduce.sh         # also checks that the published reports and the app's numbers still match their files
```

### <samp>hafiz@amanah-wallet:~$ cat ./rules</samp>

- **No secrets in the repository.** Keys live only in `.env`, which is ignored. Run `gitleaks detect` before you push.
- **No model names in code.** They come from `.env` (decision B-6), and every reply records the model that served it.
- **The contract's limits are the guarantee.** A change to `AmanahVault.sol` needs a test that fails without it, and the invariants must still hold (`forge test --match-contract Invariant`).
- **Do not tune a prompt to the red team's cases.** That fits it to the test set (decision C-16). A prompt change is measured on cases written after it.
- **New attacks go in `redteam/gallery/drafts/`** and count only after review; the published runs keep the cases they were run on.
- **Published results are not rerun for a better number.** A new run gets a new id, and the report says how it differs from the protocol.
- **Every decision goes in `docs/decisions.md`** with what it cost, and every claim in a document gets a row in `docs/claims.md`.
- **Plain sentences.** Numbers come from the run files (`frontend/src/data/facts.json` is generated, never typed).

### <samp>hafiz@amanah-wallet:~$ cat ./licence</samp>

By contributing you agree that your work is released under the [MIT licence](LICENSE), as the rest of the repository is.
