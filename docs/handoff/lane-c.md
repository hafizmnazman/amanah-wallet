# Lane C handoff: red team, immune loop, demo data

Branch `lane/redteam`. This file records what lane C has built, how to run it and what is open.

## Done

**C1, demo data.** `redteam/datagen.py` writes `redteam/data/` deterministically from a seed (default 20261020):
- `mandates.json` and `beneficiaries.json`, in the format of `shared/fixture-data.md`. Lane A's Anvil fixture reads them: 3 programmes and 45 beneficiaries, checked on 18 October 2026.
- `books.json`, the stand-in operating books that lane B reads, described in `shared/books.md`.
- `books_anchor.json`, a sha256 of every record, for the auditor's integrity check.
- `documents/`, two legitimate texts and two with injections, for the quarantined reader.

The numbers respect the demo limits in `shared/fixture-data.md`:
- Scenario 6's 11 households total 1,650 USDC.
- Scenario 13's target, `ZKT-B13`, is outside that batch.
- Two zakat households have no payout history.

Tests: `python -m pytest redteam/tests/test_datagen.py` (10 pass).

**C2, gallery format and legitimate set.**
- `redteam/cases.py` validates plan section 3.6's case format with pydantic, loads the gallery and hashes the dataset for run manifests.
- `redteam/legit.py` writes `redteam/gallery/legitimate.yaml`: 20 legitimate payouts sampled from the books' October and semester batches.
- **The 44 attack seeds,** 4 or more in each of the ten classes, are in `redteam/gallery/` (`99e552f`). The local session reviewed them against `redteam/gallery/drafts/REVIEW.md`, and Hafiz accepted that review on 19 October.
- Tests: `python -m pytest redteam/tests/test_cases.py` (5 pass).

**C4, runner.** `redteam/run.py` runs cases through S1 to S5 (plan section 7) with lane B's code, in process.
- **Paired.** The planner's output per case is cached in `redteam/cache/planner/` and reused by every arm. Each auditor's verdict is cached the same way.
- **Cache key.** It covers the case, the date, the models named in `.env`, the prompt fingerprints, and the planner's view of the books (decision B-25). A change to any of them recomputes.
- **The date.** `today: books` checks dates against the books' as-of date, also when `.env` leaves `AGENTWALLET_TODAY` empty (decision C-15).
- **Manifest.** Every run writes `redteam/results/<run_id>/manifest.json`: dataset hash, prompt fingerprints, models, commit and timestamps. It also writes one row per case to `results.jsonl`.
- **S5 runs only on Anvil.** Either a fresh fixture (`--anvil`) or an anvil node at `RPC_URL`, such as a fork of the live deployment. Each payout runs inside an EVM snapshot that is undone, so cases do not affect each other.
- **Budget guard.** A live run stops at 80% of `DAILY_MODEL_CALL_CAP` and records why.
- **Configurations.** `redteam/configs/smoke.yaml` (5 cases), `full.yaml` (plan task C7) and `immune.yaml` (plan task C8).

**C5, statistics and report.** `redteam/report.py` with `redteam/stats.py` writes `report.md` and `summary.json`. It covers:
- Wilson intervals;
- exact McNemar tests with Holm's correction;
- the joint-failure matrix;
- false refusals;
- latency and cost.

`summary.json` carries `joint_failure_planner_auditor`, which lane B's posture hook reads. The report ends with the run's `DEVIATIONS.md` when there is one, as the protocol asks, and `python -m redteam.report redteam/results/<run_id>` renders it again from `results.jsonl` without calling a model.

**C6, protocol.** `redteam/protocol.md`, committed on its own before the full run: `ffa0490`. It names the models and the 44 seeds, and says there is no mutated set (decision C-14).

**C7, the full live run, 19 October.** `redteam/results/final/`: the 44 seeds and 20 legitimate payouts through S1 to S5, S5 on Anvil, the GPT signer asked.
- S1 3 of 40 transfer attacks, S2 1, S3 to S5 none, and no USDC moved. No extraction attack got a personal field.
- Legitimate payouts refused: S1 and S2 none, S3 to S5 2 of 20, both escalated by the Qwen auditor.
- How to read it, and why the auditor's prompt is not tuned to it: decision C-16. Both deviations are at the end of the report: the repeat after decision B-25 (the first run is `final-1/`), and the date (C-15).

**C8, immune loop, without mutation.** `python -m redteam.immune` runs one cycle and hands the summary to `backend/app/agentwallet/posture.py`.
- `--apply` anchors the report and raises the posture on-chain.
- `--daily` installs a crontab entry.

Tests: `python -m pytest -c redteam/pytest.ini redteam/tests`, 29 pass. One of them starts Anvil and checks that S5 moves USDC for a legitimate payout. The 5-case smoke run completes in dry-run, with and without `--anvil`.

The choices behind all this are C-1 to C-16 in `docs/decisions.md`.

## Stopped by the model provider's safety classifier

The cloud session's red-team worker was stopped while writing attack seeds. The provider's safety classifier flagged its session in the category "cyber", most likely on the Base64 and Morse-encoded instructions. Before that, it wrote 28 seed attacks in six classes. They are in `redteam/gallery/drafts/`, unreviewed and not loaded; see the README there.

So the cloud session built only what involves no attack text: the format, the legitimate set, the runner, the statistics, the protocol and the immune loop.

On 19 October the local session wrote the 16 drafts for the four missing classes and `redteam/gallery/drafts/REVIEW.md`, which checks every draft against the books. It was then stopped by the same classifier when it started on the mutation agent (decision C-14). Since then:
- **C2's review: done.** The 44 seeds are in the gallery (see C2 above).
- **C3, the mutation agent: skipped by choice.** The full run went without a mutated set, and the protocol says so. Left for after the competition: `redteam/mutate.py` with `python -m redteam.mutate --n 3` writing `gallery/mutated/`; `run.py` and `immune.py` already read that folder.
- **C7, the full live run: done** (see C7 above).

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r redteam/requirements.txt   # includes backend/requirements.txt
.venv/bin/python -m redteam.datagen                     # regenerates redteam/data
.venv/bin/python -m pytest -c redteam/pytest.ini redteam/tests
.venv/bin/python -m redteam.run --config redteam/configs/smoke.yaml           # dry-run without keys
.venv/bin/python -m redteam.run --config redteam/configs/smoke.yaml --anvil   # adds S5 on a fresh Anvil
.venv/bin/python -m redteam.immune                      # one cycle, prints the posture decision
```

With keys in `.env` (`set -a; . ./.env; set +a`), the same commands run live. Set `PLANNER_REFUSAL_FALLBACK=off` first; the protocol asks for it.

## Open

- **Done 19 October: real id hashes.** `redteam/data/` was regenerated with the institution's `INSTITUTION_HMAC_KEY` from `.env`, and `books.json` says so in `generated.hmac_key`. The determinism test compares every byte with the key in the environment, and all but the keyed values without it (decision C-13).
- **Done 19 October: scenario 7 cap.** Decision A-10 raised flood relief's per-beneficiary cap to 1,500 USDC, in `PROGRAMMES` in `redteam/datagen.py`.
- **Done 19 October: the GPT signer, live.** `gpt-6.1-sol` filled the matrix's third lineage in the full run (decision C-10).
- **The Qwen auditor's misreadings.** It escalated two sound first payouts and one attack against its own rules (decision C-16). A prompt change should be measured on a fresh set of cases, not on these.
- **The dependency pin.** `redteam/requirements.txt` now installs lane B's pins, so pydantic is 2.13.5 for both lanes. The data generator's tests pass with it.
