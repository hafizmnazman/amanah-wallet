# Draft attack cases: not reviewed

The cloud session's red-team worker wrote these 28 seed attacks on 18 October 2026, in six classes: authority, direct injection, document injection, induced transfer, stored injection and urgency. Its session was then stopped by the model provider's safety classifier (category "cyber") while it was writing encoded payloads. No one has reviewed these files since.

`redteam.cases.load_gallery()` reads only `redteam/gallery/*.yaml`, so nothing here counts until a person has read it. To use a file, review every case, then move it up one folder.

Still missing for plan task C2 (at least 40 seeds across the ten classes of plan section 3.6): `encoded`, `data_extraction`, `privilege_escalation` and `structuring`, and more cases in the six classes above. Write these in the local session, or by hand. Writing encoded or mutated attack text with a model may trigger the same classifier.
