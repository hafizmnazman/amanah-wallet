# Paths

Where things are in this repository, and how the plan maps onto it. The plan says to update this file whenever one of its steps does not match the repository, so keep it current.

## How the plan maps onto this repository

`IMPLEMENTATION_PLAN.md` was written for a branch of the Amanah repository. This is a separate repository made for the competition, so read the plan with these differences.

| the plan says | in this repository |
|:--|:--|
| branch `fintechathon`, cut from `operating-books` | `main` |
| lane branches off `fintechathon` | `lane/contracts`, `lane/backend`, `lane/redteam`, `lane/frontend` and `lane/release`, all cut from `main` |
| Z1: decide the Amanah UI redesign, then branch | The redesign belongs to Amanah and does not apply here. The rest of Z1 (gitleaks clean, `.env` ignored) still applies. |
| the existing backend, operating books, agents, eval harness and chain queue | Not here yet. Copied from Amanah when a task needs them, and listed in `docs/borrowed.md`. |
| `README.md` is the submission's README | The draft is `docs/submission-readme.md`. `README.md` is the repository's own page until task E4 merges the two. |
| a backend baseline of 441 tests | No tests yet. |

## Where things are

| what | path |
|:--|:--|
| rules for every session | `CLAUDE.md` |
| the plan | `IMPLEMENTATION_PLAN.md` |
| environment variables, no values | `.env.example` |
| settings for Claude Code sessions | `.claude/settings.json` |
| code copied from Amanah, with sources | `docs/borrowed.md` |
| README art and its builder | `.github/readme/` |

Each lane adds its own rows as its folders appear.

## Test commands

None yet. Each lane adds the command for its suite here.
