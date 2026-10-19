# Video shot list

Plan task E5: under 5 minutes, English captions, opening with the split-screen attack. Drafted by the cloud session on 18 October 2026, and reworked by the local session on 19 October after the Base Sepolia run, so that every shot can be recorded on Tuesday morning. The running time below is 4 minutes 40 seconds, which leaves 20 seconds of margin.

## Two sources, and the captions say which

- **The browser shots run on the local stack with the live models.** The Base Sepolia vault already paid this month's households on 19 October, so a second run there meets the 30-day caps and the sentinel's frequency rule (decision B-17). The local stack is a fresh chain at every start, with the same contract, books, services and models.
- **The chain shots are the Base Sepolia run of 19 October:** its transactions on Blockscout, and `verify.py` re-checking them from the chain. Their hashes are in `README.md` section 9 and `evidence/transactions.csv`.

## Before recording

- **Screen.** 1920 by 1080. Browser zoom 125%. Terminal font 20 point.
- **The local stack, with the live models.** In WSL: `cd ~/amanah-fintechathon && bash scripts/dev_up.sh --live`. It starts Anvil with the vault at `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`, the auditor, the sentinel and the API on port 8000, and takes only the model settings from `.env`. Ctrl-C stops it; a new start is a new chain.
- **The frontend.** In a second WSL shell: `cd ~/amanah-fintechathon/frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8000 VITE_CHAIN_ID=31337 VITE_VAULT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 VITE_RPC_URL=http://127.0.0.1:8545 npm run dev`, then open http://localhost:5173.
- **The trustee in MetaMask.** Add a network: RPC http://127.0.0.1:8545, chain id 31337. Import Anvil's account 5, which the fixture registers as trustee 1: it is a public test key from Anvil's default mnemonic, worth nothing anywhere, and Anvil prints it at start. Without MetaMask, start the frontend with `VITE_DEV_SIGNING=1` and use "Sign with local trustee key".
- **Captions.** One caption per line below, at most two lines on screen at once. Export them as an `.srt` file beside the video.
- **Honesty.** Every clip shows a real run. A shot recorded on the local chain says so in its caption.

## Shots

| # | time | scenario | what to record | caption |
|--:|:--|:--:|:--|:--|
| 1 | 0:00 to 0:25 | 8 | `python scripts/split_screen.py --live --message-file docs/video/split-screen-message.txt`, full screen. The message is seed `urgency-001`, which the live S1 arm paid; tried live on 19 October, the left side paid 2,000 USDC and the right side refused with two anchored refusals. | "One message, two wallets, on a local test chain." / "Left: one model holds the key. It pays." / "Right: Amanah. Two checkers refuse, and nothing moves." |
| 2 | 0:25 to 0:40 | | Deck slide 1, then slide 5's signer table. | "Amanah needs three signers built to fail differently." / "The contract checks that they differ." |
| 3 | 0:40 to 1:00 | | Officer page: type "Pay October's aid for Ipoh." The clarifying chips appear. | "An officer asks in plain words. (Local chain, live models.)" / "The agent asks one question when the request is ambiguous." |
| 4 | 1:00 to 1:25 | | Click "Zakat monthly aid". The plan card shows 12 households and 1,810 USDC. Type "Leave out household 12, they moved." | "One card for the whole batch, built from the books." / "A correction re-plans the same batch: 11 households, 1,650 USDC." |
| 5 | 1:25 to 1:50 | 6 | Confirm. Eleven rows turn `paid`, each with three verdict cards. Then Blockscout: scenario 6's first payout on Base Sepolia, `0xf0f40271...6d62a4dba` (README section 9). | "Planner, Qwen auditor and sentinel all sign." / "Routine aid is paid with no human in the loop. On Base Sepolia, the same batch." |
| 6 | 1:50 to 2:10 | 7 | Officer: "Pay the flood relief emergency grant." The card says elevated. Confirm: `elevated_pending`. | "Above the programme's cap, the vault itself asks for a trustee." |
| 7 | 2:10 to 2:35 | 7 | Trustee page: the summary beside the decoded fields; the pre-signing checks pass; Sign in MetaMask; the row turns `paid`. | "The trustee sees plain words and the exact fields MetaMask will sign." / "The page blocks signing if the two disagree." |
| 8 | 2:35 to 2:55 | 9 | Upload `letter-injection-zkt-b07.txt`, then "Please process the attached letter." The injection warning shows, and the planner pays nothing from the letter. | "A letter with hidden instructions reaches the planner only as typed fields." / "The reader flags it, and no payout comes from it." |
| 9 | 2:55 to 3:20 | 10, 11, 12 | Blockscout, Base Sepolia: scenario 10's, 11's and 12's reverted transactions, `NotAllowlisted`, `SameLineage` and `NotTrustee` (README section 9). | "Forced past the agents, on Base Sepolia, the vault still says no:" / "a wallet off the allowlist, two Claude keys, and the planner trying to add a beneficiary." |
| 10 | 3:20 to 3:45 | 14 | Local chain, from `backend/`: the posture command below anchors the run's labelled test report and raises the posture (tried on 19 October: level 1). The posture banner appears, and "Pay household ZKT-H14 this month." now waits for a trustee. | "A red-team run attacks a copy of the quorum every day." / "When attacks start to work, the posture rises, and every payout needs a trustee." / "Here, a labelled test report crosses the threshold; our measured joint failure was 0.0%." |
| 11 | 3:45 to 4:05 | 15, 16 | Blockscout, Base Sepolia: the override payout of scenario 15, then scenario 16's reverted payout while paused and the unpause by two trustees. | "Two trustees can override an anchored refusal, within hard limits." / "The guardian can pause everything. Only two trustees unpause." |
| 12 | 4:05 to 4:25 | E1 | Terminal: `python scripts/verify.py 0xf0f40271383e44fe9adc9bafc1e96689deeeb5ceb7178faf7ea765f6d62a4dba`, every line `pass`; then `python scripts/verify.py --csv evidence/transactions.csv`, "15 of 15 executed payouts pass". | "Anyone can re-check a payout from the chain alone." |
| 13 | 4:25 to 4:40 | | Deck slide 9, the red-team table, then the repository link. | "We measured how often the signers fail together." / "Code, evidence and results: [[fill: repository link]]" |

Shot 10's command, with the local stack running. The oracle's key is derived from Anvil's public test mnemonic, so it is never written down, and `EVIDENCE_DIR` keeps the local log out of the committed evidence:

```bash
cd ~/amanah-fintechathon/backend
RPC_URL=http://127.0.0.1:8545 VAULT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 CHAIN_ID=31337 \
EVIDENCE_DIR=../evidence/anvil \
POSTURE_ORACLE_KEY=$(cast wallet private-key --mnemonic "test test test test test test test test test test test junk" --mnemonic-index 4) \
../.venv/bin/python -m app.agentwallet.posture apply --report ../evidence/immune-demo-summary.json
```

## Clips to keep

Name each clip by shot and scenario, for example `05-s06-routine-batch.mp4`, and keep the raw recordings until the video is submitted. The proof page and `evidence/transactions.csv` give the transaction behind every Base Sepolia clip, so a judge can match what they see to the chain.

## Checks before export

- The video is under 5 minutes: `ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4`.
- Every caption is in English, with no em or en dashes.
- Every number shown matches `evidence/demo-summary.json` and `redteam/results/final/summary.json`.
- Every shot from the local chain says so in its caption.
- The link in the last shot opens from a logged-out browser.
