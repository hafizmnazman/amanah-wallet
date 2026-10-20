# Deviations from the variants protocol

What differed from [redteam/protocol-variants.md](../../protocol-variants.md) in this run, and why.

1. **The day's model-call guard stopped stage 1 at 162 of the 300 drawn.** The protocol's budget rule (`redteam/protocol.md`, Budget) stops a run when the day's model calls reach 80% of `DAILY_MODEL_CALL_CAP`, which `.env` set to 600. The run stopped after 480 calls and US$6.36, shortly before 08:05 in Kuala Lumpur, and recorded the reason in its manifest. Hafiz approved raising the cap to 1,200 for one resumed run. It resumed at 10:59 with `DAILY_MODEL_CALL_CAP=1200` set for that process only; `.env` was not changed. The 162 finished cases came back from the runner's cache unchanged, and the other 138 ran then. The stopped pass's files are kept here: `stopped-manifest.json`, `stopped-summary.json` and `stopped-report.md`.
2. **Stage 2 did not run.** The protocol lets it run if the day allows. Hafiz kept the budget to stage 1, about US$12 of Claude calls, so the second 300 were never drawn.

No case was replaced, dropped or answered twice. The models and prompts are the final run's, as `manifest.json` records.
