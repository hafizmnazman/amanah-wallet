# The first full red-team run, replaced

Run on 19 October 2026 from 17:15 Malaysia time, under the protocol of commit `ffa0490`, with the 44 reviewed seeds and the 20 legitimate cases. It is kept unchanged as the record of a protocol deviation.

**What it measured.** Transfer attacks succeeded in 3 of 40 cases with the planner alone (S1), 1 of 40 in S2, S3 and S4, and 0 of 40 in S5. No funds moved, and no extraction attack leaked a personal field.

**Why it was replaced.** All 20 legitimate payouts were refused, in every arm. The planner asked for each household's amount instead of paying it, because its view of the books listed each batch as a count and a total, without the households' lines. That was a fault in the product, not in the cases, so it was fixed (decision B-25), and the full run was repeated as `redteam/results/final/`.

The protocol forbids rerunning for a better number. This was a rerun after a fix, so both runs are kept and reported.
