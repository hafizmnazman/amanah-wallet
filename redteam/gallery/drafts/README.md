# Draft attack cases: reviewed and moved

The 44 seed attacks drafted here moved up to `redteam/gallery/` on 19 October 2026:
- the cloud session's 28, written on 18 October in six classes: authority, direct injection, document injection, induced transfer, stored injection and urgency;
- the local session's 16, written on 19 October: `encoded`, `data_extraction`, `privilege_escalation` and `structuring`, 4 each.

How they were reviewed, as `redteam/protocol.md` records it:
1. A script checked that every file loads with `redteam.cases`, every `beneficiary_ref` exists in the books, every transfer goal is above what the books pay that household, and every encoded payload decodes to the instruction in its comment.
2. The local session, a Claude session, read every row against the four questions in `REVIEW.md`, and all 44 passed.
3. Hafiz accepted that review rather than reading every row, to keep the 20 October submission on time.

`REVIEW.md` stays here as the record. New drafts go in this folder and count only once reviewed and moved up.
