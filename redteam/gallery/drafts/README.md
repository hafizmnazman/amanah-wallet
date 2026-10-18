# Draft attack cases: not reviewed

44 seed attacks across the ten classes of plan section 3.6, waiting for a person's review:
- the cloud session's 28, written on 18 October 2026 in six classes: authority, direct injection, document injection, induced transfer, stored injection and urgency;
- the local session's 16, written on 19 October 2026: `encoded`, `data_extraction`, `privilege_escalation` and `structuring`, 4 each.

`redteam.cases.load_gallery()` reads only `redteam/gallery/*.yaml`, so nothing here counts until a person has read it. `REVIEW.md` lists every seed on one line, with the checks already run by script. To use a file, review every case in it, then move it up one folder:

```bash
git mv redteam/gallery/drafts/<file>.yaml redteam/gallery/
```

The protocol needs at least 40 reviewed seeds with at least 4 in each class (`redteam/protocol.md`), and `python scripts/preflight.py --stage redteam` checks it.
