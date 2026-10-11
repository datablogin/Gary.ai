# Cycle 2 independent protocol and workflow QA

Status: **PASS for the bounded protocol/workflow cycle; no unresolved blocking QA findings.**

QA owns this report and optional isolated probes under ignored `private/cycle-2/qa/`; implementation and developer tests remain untouched. All probes target the approved review seams or HTTP workflow. Any submitted QA labels are functional agent inputs, not Gary labels or independently blinded visual ground truth.

## Prior exposure

During protocol review, QA read the research note's aggregate and symbol-specific enrichment-selection discussion. QA has not inspected raw detector predictions or the case identity map. QA later read sanitized anonymous card JSON for structural checks, without making visual chart judgments. Accordingly, this role assesses protocol, HTTP behavior and persistence rather than providing primary blinded chart judgments.

## Required checks

- Reviewer cards, own-label responses and progress expose no identity, calendar date, raw price/volume, detector evidence, stratum, holdout content, other-reviewer answer or score oracle.
- Offsets are confined to the visible context/target band; locked/unknown cases and malformed labels cannot change label state.
- Exactly two registered reviewers contribute only exact certain consensus; pending, uncertain, invalid and disputed cases remain unscored.
- Identical saves are idempotent; conflicting changes require an explicit revision with the correct current revision; history and reviewer roles survive reload.
- Review reads/writes leave the synthetic paper portfolio and detector unchanged.
- Isolated-study fault injection checks authoritative-journal recovery, stale/missing materialized caches, partial trailing journal records and same-request retry without silent loss or duplicate revisions.

The implementation and developer tests were not edited by QA. Reusable independent probes are ignored under `private/cycle-2/qa/` and contain only synthetic fixtures or structural/workflow assertions.

## Coverage boundary recheck

`uv run pytest tests/test_coverage.py -q` reported **140 passed**.

Independent calls to `coverage_report` used the product's existing synthetic snapshot, without importing developer test helpers. At cutoff 2026-10-09, changing either `latest_reported_period.verified_as_of` or `headquarters.lookback_end` to 2026-10-10 produced `buy_allowed=false` and the corresponding field status `future`, preserving input dictionaries. Changing latest verification to 2026-10-08 produced `stale`. The unchanged current-cutoff control still passed coverage. These changes therefore block future review evidence without breaking the existing synthetic baseline.

## Reviewer HTTP checks

QA instance: `uv run python -m gary.preview --port 4177 --study-dir private/cycle-2/qa/recovery --reviewer agent-qa`. This study is an isolated copy; the real Gary study and the coordinator's separate browser copy were not modified.

Command: `uv run python private/cycle-2/qa/check_readonly.py`.

All **15** public cards contained exactly 180 normalized bars with offsets −179 through 0, first visible close 100 and the common −19 through 0 target band. Card fields contained no ticker/source identity, calendar dates, raw price/volume, predictions, pivots, sampling memberships or holdout metadata. The reviewer response was a strict projection of assigned identity/role, anonymous order, own labels and progress.

Source inspection identified the initial freely selectable reviewer identity as a blinding bypass before the public deployment. The coordinator bound identity to the server. The final external checks confirmed other-reviewer GETs and POSTs return 403; the page displays an assigned identity instead of a selector. Guessed locked and unknown card IDs return the same 404 response. Report, summary, queue and holdout routes return 404; foreign Host reads and foreign-origin label writes return 403. Save/revision responses never disclosed comparisons or another reviewer's answer, preventing a score oracle. Read-only requests left study files unchanged.

## Labels and isolated recovery faults

Command: `uv run python private/cycle-2/qa/check_writes_recovery.py` against a fresh isolated study. It intentionally refuses an already labeled study rather than replacing prior evidence.

- Unknown/locked IDs, unsupported decisions, completed-with-no-events, nonempty events on uncertain labels, future/outside-band/boolean offsets, excessive rationale and invalid revision controls failed without journal changes.
- First save created revision 1; identical retry left the journal unchanged. A conflicting replacement failed until an explicit current revision was supplied. Revision 2 preserved the old observation; stale conflicts failed and identical revision retries remained idempotent.
- Materialized `labels.json` was externally renamed away, then separately replaced by a stale fixture. Journal-based GET retained revision 2 in both cases. Identical retries reconstructed the proper materialized history without duplicate journal entries.
- An incomplete final journal record was externally appended. Reads ignored it. A subsequent valid save archived those exact interrupted bytes, truncated the tail and appended a complete recoverable record.
- An empty directory at `labels.tmp` forced cache replacement to fail **after** the authoritative journal append. The response was an error, while replay recovered the committed observation. Removing the obstruction by renaming that directory and retrying the identical request repaired the cache without adding another revision or journal record.

Final isolated evidence contains three functionally labeled cards, four history/journal records and latest revisions 1, 1 and 2. Decisions were only `uncertain` and `invalid`, with rationales explicitly identifying functional QA rather than chart judgments. A fresh process on port 4178 replayed this history successfully and left the journal unchanged; QA stopped that temporary process afterward.

## Independent pure-seam checks

Command: `uv run python private/cycle-2/qa/check_pure.py`.

Independent synthetic inputs checked deterministic rebuilding, source-order invariance, immutable inputs and full-context chronological purge. Empty, single-reviewer, uncertain, invalid and exact-offset-disputed cards contributed no recognition denominator. Two exact `none` labels produced one agent-only consensus case, without human-supported provenance.

Manufactured synthetic prediction metadata tested matching arithmetic separately from chart geometry: reversed event order normalized correctly; two labels and two predictions matched one-to-one with signed delays of one session; an availability before independent completion became unmatched. Dual random/enriched membership remained separate descriptive strata, and one consensus card did not become two global consensus cases. Summary calls did not mutate inputs. No real detector answers were used in these fixtures.

## Portfolio isolation and final evidence

The paper state was already $193,280 with one holding and execution date 2026-10-12 when the recovery probes began. Its initial and final SHA-256 were identical:

`b294784a288415a6eb3870834c625108a5955ab31dfcc431440deff5fc62e5c8`

Cycle-2 QA made **no** `/api/run` or `/api/reset` requests. Review writes and fault injection also preserved the detector and frozen queue bytes. The shared paper state was not reset.

Final `uv run pytest -q` reported **264 passed** (coverage 140, patterns 42, portfolio 50, review 32). `git diff --check` passed. The read-only HTTP probe passed again after all writes/faults. The coordinator independently owns browser visual verification, final commit and remote persistence.

This verdict establishes the documented local workflow and tested recovery behavior. It does not establish Gary-aligned visual labels, recognition accuracy, whole-universe coverage, an untouched financial holdout, or investment performance.
