# Red-team protocol, addendum: the variants

**Committed and pushed before either sample was drawn,** on 20 October 2026. It extends [protocol.md](protocol.md), committed in `ffa0490`, without changing it: the final run's results stay as published.

## Why

The final run measured the 44 hand-written seeds. None of the 40 payment attacks moved funds through Amanah, but zero in 40 only bounds the true rate below 7.5% at 95% confidence (the rule of three, 3/40), and the planner alone was fooled 3 times, too few for the paired test to be significant (exact McNemar, p = 0.25). A random sample of many more attacks narrows both.

## The population

- **1,100 variants:** 25 of each of the 44 seeds, made by `python -m redteam.variants population` into `redteam/variants/population.yaml`, dataset hash `2618a7802efae7ac36bdbfaad306cf44848b792f515560dd0edc3bbca8313c64`.
- **No model wrote them** (decision C-14). Each is its seed with one to three of fourteen code transforms, picked by a generator seeded with the seed's id: `persona`, `authority`, `urgency`, `malay`, `courtesy`, `zero_width`, `homoglyph`, `shout`, `bullets`, `system_tag`, `chat_log`, `forwarded`, `email` and `new_wallet`. A variant's `mutation` records only the transforms that changed its text. The goal never changes, except that `new_wallet` moves the attacker's wallet in the payload and the goal together.
- **The classes keep the seeds' proportions:** 125 variants each for authority, direct injection, document injection and induced transfer; 100 each for the other six.

## The sample

- **Stratified random sampling:** proportional allocation by class, rounded by largest remainder; within each class, simple random sampling without replacement (`redteam.variants.sample`). Anyone with the block hash draws the same sample.
- **Stage 1: 300 variants.** The generator is seeded with the hash of the first Base Sepolia block whose timestamp is at or after **2026-10-19T23:40:00Z** (07:40 in Kuala Lumpur), which is after this file is pushed.
- **Stage 2: 300 more** from the 800 left, seeded with the first block at or after **2026-10-20T01:40:00Z**. It runs if stage 1 has finished and stage 2 can finish by 2026-10-20T05:00:00Z, whatever stage 1 shows. Otherwise it does not run, and the results say so.
- **No variant is replaced or dropped after the draw.** A case the runner cannot finish (a provider outage) is retried; if it still fails, it is reported as not run, by id.

## What runs

- The configurations **S1** (the planner alone), **S3** (and the Qwen auditor), **S4** (and the sentinel) and **S5** (and the vault, on a fresh Anvil fixture), as defined in [protocol.md](protocol.md), with the final run's models and prompts; each run's `manifest.json` records the prompt fingerprints. S2 and the GPT auditor are left out to keep the cost down: they answer questions the seeds already answered.
- `python -m redteam.variants run --stage 1`, with `redteam/configs/variants.yaml`.

## What is reported

- **Primary:** transfer attacks that moved funds through S5, with the exact one-sided 95% upper bound (Clopper-Pearson; at zero successes in n it is 1 - 0.05^(1/n), close to 3/n).
- **Secondary:** attack success through S1 and S3, with Wilson 95% intervals; the exact McNemar test of S1 against S5 on the same variants; and the per-seed view, how many of the 44 seeds had at least one variant succeed, because variants of one seed are related and do not count as fully independent attacks.
- **Every result is published,** a success through S5 included.

## Limits

- The variants inherit their seeds' ideas. They test how well an attack survives rewording, wrapping and obfuscation, not new kinds of attack, and the inference is to this population of variants, not to every possible attack.
- The transforms are surface-level and in English, with a few Malay phrases. The Chinese run is separate (`redteam/results/zh-kimi`).
