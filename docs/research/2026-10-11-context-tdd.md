# Context wrapper observed TDD evidence

Seams were confirmed in the approved plan and coordinator assignment:
`build_review_queue(series, config)`, `record_review_label(queue, labels, entry)`,
and `summarize_review(queue, labels)` in `gary.context_review`.
Read the TDD skill, its tests/mocking guidance, and project `CONTEXT.md` first.
Only synthetic sources, synthetic annotations, and public interfaces are used.
Frozen `review.py`, `evaluation.py`, and `patterns.py` are untouched.

1. **Preserved parent and historical anonymous overview**: new test first failed
   collection because `gary.context_review` did not exist. Added the minimum
   queue builder. A fixture assertion then exposed a test mistake: first volume
   need not equal the median in a mixed-volume window. Removed that incorrect
   assertion (dedicated median behavior is covered in a later slice).
   Observed green: `uv run pytest tests/test_context_review.py -q` → **1 passed**.

2. **Explicit protocol and validated released parent**: parameterized the one
   configuration boundary. Observed red: **4 failed, 2 passed** (wrong profile,
   bad release hash, extra config, and unreleased parent were accepted).
   Added strict three-field config and parent validation through the existing
   public empty-label summary. Observed green: **6 passed**.

3. **Validate all retained source input**: one parameterized source-admission
   test failed in all 18 controls (**18 failed, 6 passed**), including malformed
   bars outside the historical window. Added full ordered/canonical OHLCV,
   provenance/timezone/split, unique identity, and parent identity validation.
   Observed green: **24 passed**.

4. **Historical coverage and final-180 reconciliation**: all five controls
   initially failed (**5 failed, 24 passed**). Added minimum 1,200 sessions,
   seven-day start bound, source history before the open-left anniversary,
   exact original cutoff, and literal original-window equality.
   Observed green: **29 passed**.

5. **Bound observation provenance/retry/revision**: observed red **1 failed,
   29 passed** because the label seam was absent. Delegated the frozen decision
   and revision contract, then stamped only newly generated rows from the
   queue's protocol/overview. Caller stamps are ignored. Observed green:
   **30 passed**; exact retry stays idempotent, revision retains prior rows.

6. **Submission view binding**: observed red **3 failed, 30 passed** for
   missing, stale, and original-parent tokens. Added the exact current queue
   token requirement before core label recording. Observed green: **33 passed**.

7. **Rehashed context tampering**: observed red **12 failed, 34 passed**;
   the core already rejected a wrong outer hash but did not own supplemental
   context validation. Added exact preserved-parent equality, metadata/source
   identities and hashes, all context bars, dates, tail reconciliation, window
   fingerprints, normalization and split offsets before label recording.
   Observed green: **46 passed**.

8. **Entire revision trail view provenance**: observed red **3 failed,
   46 passed** when a superseded row had missing/old protocol or wrong overview
   fingerprint. Added validation of every prior row before writes, including
   superseded revisions. Observed green: **49 passed**.

9. **Changed-view summary and two complete passes**: observed red **1 failed,
   49 passed** because the summary seam was absent. Added validated delegation
   of the frozen summary with explicit context phase/protocol/comparability,
   detector's 180 input sessions, overlap/unblinding and retrospective provider
   limitations. Observed green: **50 passed**; empty and one-pass recognition
   and consensus remain null, two complete synthetic passes expose agreement.

10. **Calendar and split boundary**: observed red **1 failed, 50 passed**.
    February 29 clamps to February 28, and a trading-day anniversary is
    excluded as specified. The failing control was a weekend split after the
    anniversary and before the first session. Marked its first returned session.
    Observed green: **51 passed**.

11. **Byte-sensitive preserved representation**: new rehashed controls
    replacing `1.0` with `true` in overview/original cards observed red
    **2 failed, 51 deselected**. Python value equality considers these equal;
    switched preservation and normalization comparisons to canonical JSON
    fingerprints. Observed green: **2 passed, 51 deselected**. This strengthens
    validation without changing any generated queue payload.

12. **Existing behavior cross-checks**: summary-side tampering/history
    validation, own-median/zero volume, and full uncertain/invalid/disputed
    exclusions required no additional implementation. Observed **74 passed**.
    A further literal-tail representation control observed red **1 failed,
    74 deselected** when original integer volume was replaced by an equivalent
    float. Applied canonical JSON equality to final-180 reconciliation too.
    Observed green: **1 passed, 74 deselected**; generated payload is unchanged.

Final regression run:
`uv run pytest tests/test_context_review.py tests/test_review.py tests/test_evaluation.py -q`
→ **154 passed in 21.79s**, including **75 context controls** and the preserved
review/evaluation tests. No real primary labels or predictions were read or
created. Only the assigned wrapper, synthetic test file, and this evidence note
were edited by the context developer. No commit/push was performed.

The embedded parent and source hashes provide integrity commitments, not
independent authenticity. Runtime adapters must reconstruct the expected queue
from the actual validated release and retained full sources before display or
write, as required by the approved integration contract.
