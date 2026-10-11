---
status: approved
---

# Five-year context on the historical holdout review

Human request: “Can you add the five year charts to this as well?” The open page is the 13-card holdout. Add long context ending at each original case's historical cutoff; no post-cutoff bars. Execute the requested local enhancement, preserving the original release, frozen executable sources, detector inputs, earlier labels and paper state.

## Scope and evidence

Original endpoints span 2022–2026; the current cache starts 2021-10-11, so true five-year prefixes require older source data. Research Dot makes exactly one bounded ten-year daily-chart request for each original source and records received integrity/coverage/reconciliation evidence privately. No retries after denial, subscription or SEC request. Require complete arrays, ordered dates, valid OHLCV, at least 1,200 sessions inside the five-calendar-year interval, a start no more than seven days after its anniversary, exact original end date, and exact date/OHLCV equality for the last 180 sessions. If a source fails, show a anonymous study-unavailable status rather than fabricate a full chart or stitch conflicting prices. Known split events inside the longer history are marked anonymously and retained as unverified adjustment provenance; the original 180-session windows remain unchanged.

Adding information changes visual-review evidence. Create a separate **five-year-assisted holdout** queue/journal, and tag its labels with the view protocol/hash. Preserve the original 13-card queue and agent-only observations; do not copy those observations into the new context pass or score new labels as the original same-view holdout. The original human holdout is currently unreviewed. After context exposure, its preserved UI is read-only. The user’s request authorizes this additional representation; no original label is deleted, revised or reclassified.

## Interfaces and ownership

Reuse the three already-confirmed logical seams and signatures in a versioned adapter namespace: `build_review_queue(series, config)`, `record_review_label(queue, labels, entry)`, `summarize_review(queue, labels)`. New context configuration binds the validated original released queue and release hash. The wrapper module owns additional view validation and provenance; original `review.py`, `evaluation.py` and `patterns.py` remain byte-identical, so the existing release continues to validate. No new strategy/freeze/evaluation interface is introduced.

- Research Dot: bounded source retrieval/structural checks and `docs/research/2026-10-11-holdout-context-data.md`. No product code/tests or primary labels.
- Context developer: new `src/gary/context_review.py`, public-seam tests in `tests/test_context_review.py`, observed vertical red/green evidence. Normalized full-context overview is private until projected, while `cards` retain exact original 180-session payloads. Additional sealed view metadata changes the queue hash; label history stamps the exact view/profile and cannot replay against the original queue.
- Coordinator: `load_labels`/`save_label` dispatch, anonymous `reviewer_view` projection, `cycle3_study` alias/runtime checks and adapter/CLI in review_preview.py, fixed-whitelist API routing in preview.py, overview/detail rendering in review.html, local deployment, docs and git. Each runtime read reconstructs the expected context queue from the validated original release and retained older raw sources before display. Same-input rebuilds preserve labels; drift cannot replace an active queue. Current `study=holdout` selects the context-assisted pass once built, while a separately named original holdout view is read-only.
- Independent QA: non-author protocol review, synthetic public-seam/HTTP/source/persistence probes, original hash guard, browser check. No real primary labels interpreted.

## Representation and validation

For each case use open-left `(cutoff minus five calendar years, cutoff]`, February 29 anniversary clamped to February 28. Normalize overview OHLC to its own first close 100 and volume to its own median. Preserve the original detail card exactly; explain the separate index bases in the chart note. Both charts share final-session offset zero. Show the final20 band and anonymous relative-offset split markers. Reveal no ticker, calendar dates, predictions, sampling stratum or other-reviewer answers.

The context queue deep-copies the original held-out queue and retains its compatible original profile/case IDs, with an explicit supplemental sealed `context_review` object containing protocol, parent queue/release fingerprints, per-case raw full context/normalized overview/provenance, and source hashes. Its new queue hash binds both representations. The wrapper validates that original content still equals the trusted parent queue before calling existing label/summary logic; this is a distinct observational protocol, never a renamed original queue. Card responses also carry an opaque `view_token` equal to the context queue fingerprint. Label submissions must echo the exact token; missing or stale bindings fail before any write. This prevents an old 180-session tab from silently saving a context observation. Label entries carry `view_protocol` and `overview_hash`, generated from the queue rather than accepted from the reviewer. Replayed submissions retain their token.

Context summary identifies `phase=holdout_context`, `original_holdout_comparable=false`, and the frozen detector's 180-session input. It withholds recognition until both registered context passes are complete, with uncertain/invalid/disputed exclusions retained. Agent observations from the old view are not context observations. No independent context agent pass or measured accuracy is presumed in this UI enhancement. Retrospective expanded history can overlap previously exposed calibration history; record overlap counts and context exposure in a private study protocol, and retain this limitation in the separate summary. Any rollback keeps the original pass read-only after context exposure.

## Gates, persistence and rollback

Plan+research+scorecard+role briefs persist before implementation after three non-author lenses. User request is authorization within this bounded scope; existing confirmed queue/label/summary seams are reused. Public-seam TDD uses one failing behavior then minimum implementation, with original311 tests preserved. Runnable final checks: make verify, exact original-artifact hash guard, independent context/HTTP probes, immutable old release reproduction, same-input rebuild, future clipping, last180 reconciliation, split markers, withheld partial metrics, own-label/save/retry/revision/reload, and browser overview/detail at current viewport.

Keep all received market data, queue/view metadata and labels in ignored private/holdout-context (sources) and private/cycle-3/holdout-context (study). Preserve originals. No portfolio run/reset, brokerage, stock clearance or five-year strategy performance claim. Stop localhost to end deployment; rollback via new git commit and preserved original study key, without deleting new or old labels. Final code/docs are pushed and remote equality verified.

## Concrete verification anchors

Source evidence is `private/holdout-context/sources/validation-summary.json`: all13 context prefixes have1254–1259 returned sessions, all13 match the frozen final180 exactly, and three intersect reported splits. Calendar completeness/adjustment correctness are unverified. Adopt the research open-left interval and test a trading-day anniversary boundary explicitly. Preservation baseline is `private/holdout-context/original-hashes.json` (44 files), compared by `scripts/check_holdout_context.py` without reading observations semantically. `uv run pytest tests/test_context_review.py -q` covers the confirmed seams; `make verify` runs all tests. Independent `uv run python scripts/check_holdout_context.py` checks retained-source reconstruction, all cutoff/last180/split/anonymous projections, unchanged originals and paper. QA records isolated HTTP stale/missing/wrong-token rejection, valid retry/revision/recovery, foreign reviewer/origin and original read-only results. Full/partial synthetic context summaries verify explicit changed-view interpretation and withholding. Final actual-browser observation verifies all13 long overviews and detail/target controls; primary labels are never generated by QA.

## Review (2026-10-11)

Verdict: SHIP after one correction pass by three fresh non-author agents.

| Lens | Finding and resolution | Final verdict |
| --- | --- | --- |
| Feasibility | Existing frozen validator accepts supplemental metadata. Explicitly named adapter replay/save/projection/route ownership. | SHIP |
| Verifiability | Lower-bound interval differed from research; standardized open-left and required trading-day boundary regression. Named hash baseline and runnable checks. | SHIP |
| Scope/risk | Old-tab submission could silently become a context judgment; required exact card view token echoed on submit and checked before writing. Recorded exposure/overlap and retained read-only rollback. | SHIP |

Human authorization: the current explicit request to add five-year charts authorizes this bounded local enhancement; prior confirmed queue/label/summary signatures remain the seams. Status approved records that existing human authorization, without a new launch request. Implementation follows the reviewed corrections.
