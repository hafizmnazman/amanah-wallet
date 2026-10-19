# Video shot list

Plan task E5: under 5 minutes, English captions, opening with the split-screen attack, assembled from clips recorded as each scenario passed. This is a draft from the cloud session, 18 October 2026. The running time below is 4 minutes 40 seconds, which leaves 20 seconds of margin.

## Before recording

- **Screen.** 1920 by 1080. Browser zoom 125%. Terminal font 20 point, dark text on a light background.
- **The stack.** For Base Sepolia, `.env` filled in and the deployment done (HANDOFF items 1 to 6). For a rehearsal, `bash scripts/dev_up.sh`.
- **One run per vault.** Record the payout scenarios on their first run. A rerun on the same vault meets the 30-day caps and the sentinel's frequency rule (`docs/handoff/lane-e.md`).
- **The trustee.** MetaMask with a registered trustee account on Base Sepolia (HANDOFF item 10).
- **Captions.** One caption per line below, at most two lines on screen at once. Export them as an `.srt` file beside the video.
- **Honesty.** Every clip shows a real run. The opening's left side runs on a local test chain, and its caption says so.

## Shots

| # | time | scenario | what to record | caption |
|--:|:--|:--:|:--|:--|
| 1 | 0:00 to 0:25 | 8 | `python scripts/split_screen.py --live`, full screen. Use a message the live S1 arm fell for (`redteam/results/final/results.jsonl`, `fooled.planner` true). | "One message, two wallets." / "Left: one model holds the key, on a local test chain. It pays." / "Right: Amanah. Two checkers refuse, and nothing moves." |
| 2 | 0:25 to 0:40 | | Deck slide 1, then slide 5's signer table. | "Amanah needs three signers built to fail differently." / "The contract checks that they differ." |
| 3 | 0:40 to 1:00 | | Officer page: type "Pay October's aid for Ipoh." The clarifying chips appear. | "An officer asks in plain words." / "The agent asks one question when the request is ambiguous." |
| 4 | 1:00 to 1:25 | | Click "Zakat monthly aid". The plan card shows 12 households and 1,810 USDC. Type "Leave out household 12, they moved." | "One card for the whole batch, built from the books." / "A correction re-plans the same batch: 11 households, 1,650 USDC." |
| 5 | 1:25 to 1:50 | 6 | Confirm. Eleven rows turn `paid`, each with three verdict cards. Open one Blockscout link. | "Planner, Qwen auditor and sentinel all sign." / "Routine aid is paid with no human in the loop, on Base Sepolia." |
| 6 | 1:50 to 2:10 | 7 | Officer: "Pay the flood relief emergency grant." The card says elevated. Confirm: `elevated_pending`. This needs decision A-10 applied first. | "Above the programme's cap, the vault itself asks for a trustee." |
| 7 | 2:10 to 2:35 | 7 | Trustee page: the summary beside the decoded fields; the pre-signing checks pass; Sign in MetaMask; the row turns `paid`. | "The trustee sees plain words and the exact fields MetaMask will sign." / "The page blocks signing if the two disagree." |
| 8 | 2:35 to 2:55 | 9 | Upload `letter-injection-zkt-b07.txt`, then "Please process the attached letter." The injection warning shows; the row is `rejected` with an anchor link. | "A letter with hidden instructions reaches the planner only as typed fields." / "The sentinel refuses the second payment it asks for." |
| 9 | 2:55 to 3:20 | 10, 11, 12 | Proof page, filtered to reverted rows: `NotAllowlisted`, `SameLineage`, `NotTrustee`. | "Forced past the agents, the vault still says no:" / "a wallet off the allowlist, two Claude keys, and the planner trying to add a beneficiary." |
| 10 | 3:20 to 3:45 | 14 | The posture banner appears after the immune loop's run. A routine payout now waits for a trustee. | "A red-team agent attacks a copy every day." / "When attacks start to work, the posture rises, and every payout needs a trustee." If the run used the demo's labelled test report (decision E-5), add: "Here, a labelled test report crosses the threshold." |
| 11 | 3:45 to 4:05 | 15, 16 | Proof page rows for the override and the pause; the pause's reverted payout; the unpause by two trustees. | "Two trustees can override an anchored refusal, within hard limits." / "The guardian can pause everything. Only two trustees unpause." |
| 12 | 4:05 to 4:25 | E1 | Terminal: `python scripts/verify.py <txHash>` on the shot 5 payout, every line `pass`. | "Anyone can re-check a payout from the chain alone." |
| 13 | 4:25 to 4:40 | | Deck slide 9, the red-team table, then the repository link. | "We measured how often the signers fail together." / "Code, evidence and results: [[fill: repository link]]" |

## Clips to keep

Name each clip by shot and scenario, for example `05-s06-routine-batch.mp4`, and keep the raw recordings until the video is submitted. The proof page and `evidence/transactions.csv` give the transaction behind every clip, so a judge can match what they see to the chain.

## Checks before export

- The video is under 5 minutes: `ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4`.
- Every caption is in English, with no em or en dashes.
- Every number shown matches `evidence/demo-summary.json` and `redteam/results/final/summary.json`.
- The link in the last shot opens from a logged-out browser.
