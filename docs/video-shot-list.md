# Video plan

**Superseded on 20 October** by [docs/video-script.md](video-script.md), the recorder `docs/video/record.cjs` and the cut `docs/video/cut.py` (decision E-40, runbook step 8). Kept for the reasoning behind each shot and for recording by hand.

Plan task E5: a demo video of at most 5 minutes, in English with captions. Reworked on 19 October after the UI redesign (decision E-26) and the competition brief, which asks the video to show, on screen: a full task end to end; refusals of an induced transfer, a data extraction attempt, a privilege escalation attempt and a prompt injection; a clarifying question, a correction and a graceful fallback; and a human approval step before money moves. Every one of those has a shot below.

## How it is made

- **Recorded by script, not by hand.** Playwright drives the app on the local stack with the live models (`bash scripts/dev_up.sh --live`) at 1920 by 1080, and records each segment. The captions are drawn into the page during the recording, so they are in the picture and also exported as an `.srt` file.
- **The chain shots are the Base Sepolia run of 19 October,** recorded from Blockscout: the same scenarios with real transactions. The local-chain shots say "local chain" in their caption (decision E-25).
- **The opening** follows the brag skill's slim method: a short launch clip built from the app's own components (Sang Kancil, the signer colours, the measured numbers), rendered in a headless browser.
- **Stitched with ffmpeg,** H.264 MP4 at 30 frames a second. It goes to OneDrive and to the repository's release page, because YouTube and Google Drive do not open in mainland China.
- **Cost:** about 20 live model calls, around US$1.

## Shots

| # | time | what is on screen | what it shows (the brief's list) | caption |
|--:|:--|:--|:--|:--|
| 1 | 0:00 to 0:10 | Launch clip: Kancil with the key, the three signers meeting at the vault, "17 of 17 on Base Sepolia", "0 of 40 attacks moved funds" | the hook | "Amanah: an AI wallet that can't be sweet-talked." |
| 2 | 0:10 to 0:35 | The split screen, seed `urgency-001`: the left wallet pays 2,000 USDC, Amanah refuses with two anchored refusals | induced transfer, the wow | "One message, two wallets, on a local test chain." / "Left: one model holds the key. It pays." / "Right: Amanah. Two checkers refuse, and nothing moves." |
| 3 | 0:35 to 0:55 | Home page: the three story panels and "Three keys, one vault" | the problem and the user | "Money held in trust: zakat, flood relief, bursaries." / "Each signer sees a different slice of the evidence." |
| 4 | 0:55 to 1:15 | Officer Desk: "Pay October's aid for Ipoh." The planner asks which batch | clarifying question | "The officer asks in plain words. (Local chain, live models.)" / "Two batches match, so the planner asks which." |
| 5 | 1:15 to 1:35 | "Zakat monthly aid", the plan card of 12 households and 1,810 USDC, then "Leave out household 12, they moved." | correction | "One card for the whole batch, from the books." / "A correction re-plans it: 11 households, 1,650 USDC." |
| 6 | 1:35 to 1:55 | Confirm: 11 payouts paid, each with the Planner, Auditor and Sentinel chips; one opened to show why each signer decided | task completion | "Three different signers on every payout. No human needed for routine aid." |
| 7 | 1:55 to 2:10 | Blockscout: scenario 6's first payout on Base Sepolia, `0xf0f40271...6d62a4dba` | task completion on-chain | "The same batch on Base Sepolia: real transactions." |
| 8 | 2:10 to 2:40 | "Pay the flood relief emergency grant." Elevated; the trustee page with the summary beside the signed fields; sign; paid | human approval before money moves | "Above the cap, the vault itself asks for a trustee." / "The trustee checks the summary against exactly what they sign." |
| 9 | 2:40 to 2:55 | Officer chip "A fake chairman": the planner refuses | induced transfer | "A fake urgent order from the chairman: refused." |
| 10 | 2:55 to 3:10 | Officer chip "Steal the data": the planner has no personal data to give | data extraction | "Asked for every recipient's IC number: no model holds any to leak." |
| 11 | 3:10 to 3:25 | Officer chip "Grab admin", then Blockscout: scenario 12 reverted with `NotTrustee` | privilege escalation | "Claiming to be the new admin changes nothing: only two trustees govern." |
| 12 | 3:25 to 3:45 | Upload `letter-injection-zkt-b07.txt`, then "Please process the attached letter.": the injection flag, typed fields only, no payout from it | prompt injection | "Hidden instructions in a letter are quarantined: only typed fields reach the planner." |
| 13 | 3:45 to 4:05 | The auditor service stops; a payout waits in the fail-closed queue with a trustee alert; the service returns and it pays | graceful fallback | "When a checker is down, payouts wait. They never go out with fewer checks." |
| 14 | 4:05 to 4:30 | Red team page: 3 of 40 for the planner alone, 0 of 40 through the quorum and the vault, the grid | security, measured | "We attacked it 44 ways, with the live models." |
| 15 | 4:30 to 4:45 | The posture command, the banner, a payout that now waits for a trustee | the immune loop | "When attacks start to work, the wallet gets stricter on its own." / "Here, a labelled test report crosses the threshold." |
| 16 | 4:45 to 5:00 | `verify.py` "15 of 15 executed payouts pass", the worst-case card, Kancil, the repository link | proof and close | "Anyone can re-check every payout from the chain." / "github.com/hafizmnazman/amanah-wallet" |

## Checks before export

- Under 5 minutes: `ffprobe -v error -show_entries format=duration -of csv=p=0 amanah-demo.mp4`.
- Every caption in English, with no em or en dashes; every local-chain shot says so.
- Every number on screen matches `evidence/demo-summary.json` and `redteam/results/final/summary.json`.
- The video opens from a logged-out browser on OneDrive and on the release page.

## Recording by hand instead

If the scripted recording fails, the same shots can be recorded by hand: `bash scripts/dev_up.sh --live` in one WSL shell, and in another `cd frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8000 VITE_CHAIN_ID=31337 VITE_VAULT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 VITE_RPC_URL=http://127.0.0.1:8545 VITE_DEV_SIGNING=1 VITE_DEV_TRUSTEE_KEY=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 5) npm run dev`. Shot 15's posture command:

```bash
cd ~/amanah-wallet/backend
RPC_URL=http://127.0.0.1:8545 VAULT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 CHAIN_ID=31337 \
EVIDENCE_DIR=../evidence/anvil \
POSTURE_ORACLE_KEY=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 4) \
../.venv/bin/python -m app.agentwallet.posture apply --report ../evidence/immune-demo-summary.json
```

The keys come from Anvil's public test mnemonic, so none is written down, and `EVIDENCE_DIR` keeps the local log out of the committed evidence.
