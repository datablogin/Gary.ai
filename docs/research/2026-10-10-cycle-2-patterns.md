# Cycle 2: blinded local real-chart review

Research date: 2026-10-10, America/Chicago. This proposes the concrete form of the three user-approved [review seams](../cycle-2-contracts.md). No queue, new tests, labels or implementation were created during this research. Detector parameters remain frozen.

## Recommendation and measured constraints

Build a small, localhost-only annotation queue from the eight cached chart responses. Keep reviewer cards physically separate from private identity/prediction/sampling metadata. Open calibration cards only; do not expose, label or score the holdout in this cycle. Labels are research observations and cannot change fundamental clearance, detector settings or paper orders.

Each cache has 1,255 daily bars. The frozen first-cycle scan contains six hypotheses: two inverse and four top, no cup. All six reproduce when the current detector receives exactly the preceding **180 bars ending at the signal date**. This context-reproduction check was run through the existing public `detect_patterns` seam, without modifying it. A 252-bar view would omit the early O hypothesis or create a shorter card that could reveal selection; fixed 180-bar views are consistent and cover v1's maximum 176-session pattern/prior-trend context.

The reported O split on 2021-11-15 intersects that O hypothesis's 180-bar window, so exclude it from the primary study. META's March 2025 hypothesis falls inside the proposed temporal embargo; retain its omission privately, not as an open calibration card. Eligible enrichment is therefore three calibration hypotheses (ORCL two, TSM one) and one locked later hypothesis (ARCC). This does not classify those securities as investable; TSM/O/ARCC remain research exclusion controls.

Cached prices are **provider-received OHLC**, consistently used for chart and detector. Do not substitute dividend-adjusted close into raw OHLC. Excluding reported split-intersecting windows removes known ambiguity but does not certify adjustment accuracy, completeness of corporate-action events, or point-in-time data. This is a retrospective, frozen-snapshot recognition pilot on eight surviving securities.

## Frozen queue defaults

| Setting | Proposed value |
| --- | --- |
| Visible chart | 180 consecutive supplied sessions, clipped at its final session |
| Annotation/scoring band | Last 20 sessions, offsets −19 through 0 inclusive |
| Random sampling seed | `20261010`, private local `random.Random` instance |
| Presentation shuffle seed | `20261011`; shuffle all open cards together, not by stratum |
| Calibration final session | 2024-12-31 |
| Full-context temporal purge | A later card is admissible only if its **first** visible date is after the calibration final date |
| Whole-source reservation | AMGN and SIRI; no calibration cards from either source |
| Other six sources | Two calibration random endpoints plus one time-holdout random endpoint per source |
| Reserved sources | Three random holdout endpoints per source, over their full eligible history |
| Enrichment | All admissible frozen detections at their completion endpoints; preserve exclusions explicitly |
| Corporate-action filter | Exclude any card intersecting a reported split date, including either boundary |
| Date matching | Same kind, one-to-one, at most three sessions apart; prediction availability cannot precede independently labeled completion |
| Holdout release | Disabled; no release endpoint or toggle in this cycle |

That is **24 random selections** plus four admissible enriched selections before exact-duplicate merging: approximately **15 open calibration cards and 13 sealed holdout cards**. Sample uniformly without replacement from each fixed source/split endpoint frame, independently of detector output. Random selections may contain detections; do not condition them on being non-detections. If an enriched endpoint is also selected randomly, create one card carrying both private memberships and preserve its random-selection provenance.

At the inspected cache boundaries, nonreserved calibration frames have 632 admissible endpoints each except O (606), and the later time-holdout frame has 265 endpoints per source. The first clean later endpoint is 2025-09-22 because its 180-bar context begins after 2024-12-31. The six calibration sources therefore have 3,766 candidate endpoints; their later frames have 1,590. Reserved AMGN has 1,076 full-history endpoints; reserved SIRI has 896 after the reported split filter. These are measured input-frame counts, not resulting queue counts or estimates of independent statistical samples.

Freeze selected endpoints, ordered source identities, Python version and sampling implementation in the manifest, not just the seed. Python documents that sampling algorithms can change across versions even when a seed is retained. [Python 3.11 random documentation](https://docs.python.org/3.11/library/random.html#notes-on-reproducibility). The temporal purge is our explicit full-chart overlap rule; the general need to preserve temporal order and support a gap is also described in [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html). No scikit-learn dependency is required.

Do not claim an untouched financial holdout: developers already observed the first-cycle detector scan. The detector is frozen before independent annotations; whole-source and later-period locks protect the new labeling/calibration process. Release and any parameter change require a subsequent bounded cycle and a new study/version record.

## Exact input and queue shapes

Proposed input to `build_review_queue(series, config)`:

```text
series: list[{
  source_id: str, symbol: str, source_sha256: str,
  fetched_at: ISO timestamp, exchange_timezone: str,
  price_basis: "provider_received_ohlc",
  bars: [{date: ISO date, open, high, low, close, volume}],
  split_dates: [ISO date]
}]

config: {
  study_id: str, id_salt: str, random_seed: 20261010, shuffle_seed: 20261011,
  window_sessions: 180, target_sessions: 20,
  calibration_end: "2024-12-31", reserved_sources: ["AMGN", "SIRI"],
  calibration_random_per_source: 2, time_holdout_random_per_source: 1,
  reserved_random_per_source: 3, match_tolerance_sessions: 3,
  holdout_locked: true,
  detector_version: "causal-geometry-v1",
  detector_parameter_hash: "d1e59ce553b98cfffa41b2ce956ffdbd170f3883e9ec5a1fab6a22b91e23cbae",
  detector_source_file_sha256: "76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a",
  reviewers: {reviewer_a: {role: "human" | "agent"},
              reviewer_b: {role: "human" | "agent"}}  # exactly two distinct IDs
}
```

The adapter verifies each raw source hash before constructing this input. It computes required `detector_source_file_sha256` from the current `src/gary/patterns.py` bytes; the pure builder requires 64 hexadecimal characters and records that hash alongside the pinned version/parameter hash. The builder also hashes canonical normalized input bars/config. Use sorted keys and compact JSON with nonfinite numbers rejected; record that serialization convention. SHA-256 is available in the standard library. [Python hashlib documentation](https://docs.python.org/3.11/library/hashlib.html).

Reject invalid dates/OHLCV, duplicate source identifiers, insufficient frames, unsupported config changes and missing declared corporate-action metadata rather than silently reducing the planned sample. Sort sources and endpoint frames before seeded selection. Distinguish `split_dates=[]` with a checked source from an unavailable corporate-action response.

Returned queue is a private, immutable study object:

```text
queue: {
  schema_version: "pattern-review-v1", study_id, queue_hash,
  cards: {case_id: {
    case_id,
    bars: [{offset: -179..0, open, high, low, close, volume}],
    target_start_offset: -19, target_end_offset: 0,
    price_basis: "normalized provider-received OHLC",
    volume_available: bool
  }},
  order: [calibration case_id],
  sealed: {
    config, sources: [{source_id, symbol, source_sha256, input_bars_hash,
                       fetched_at, exchange_timezone, split_dates}],
    detector: {version, parameter_hash, source_file_sha256},
    cases: {case_id: {
      source_id, symbol, split: "calibration" | "time_holdout" | "symbol_holdout",
      memberships: ["random", "enriched"],
      start_date, as_of, source_start_index, source_end_index,
      visible_dates: [ISO date], window_hash,
      random_frame_size, random_selection_probability,
      predictions: [complete detector event in target band],
      raw_window: [provider-received bars]
    }},
    exclusions: [{source_id, event_id, reason}],
    holdout_locked: true
  }
}
```

`cards` and `order` contain **only calibration**. Holdout cards' geometry belongs only under `sealed`; they have no public chart payload. Generate opaque IDs from the study salt and hashed source/window identity, with no ticker/date/stratum prefix. Salt and unblinding map are private. Include the entire sealed object in the queue hash before labels, then persist the queue read-only. The UI receives only a selected `cards[case_id]`, never the full queue. Test both the mapping's omission and guessed holdout-ID requests.

For each card, call the frozen detector on **exactly its visible 180 provider bars** and retain all events whose completion and availability lie within the target band and no later than card cutoff. Do not score hidden earlier context or inject full-series predictions into random cards. Enriched cases must reproduce their anchor event from those same visible bars; otherwise record an exclusion `not_reproduced_in_visible_context`.

## Blinded reviewer representation

Normalize every visible OHLC value by the first visible close and multiply by 100. Normalize volume by the median volume within the clipped window; if it is zero, omit volume and flag `volume_available=false`. Detector geometry still receives the original internally consistent bars; the display uses only proportional transformations. Both use the same as-of observations, including the full last 20-session target band.

Display relative session offsets, indexed prices and normalized volume. Hide source name, calendar dates, raw prices/volume, prediction kinds, detector overlays, pivots, scores, stratum and split metadata from HTML **and network responses**. Neutral highlighting of the same last 20 sessions on every card is useful. Same shape and length for every card prevents presentation from revealing enrichment. An experienced reviewer may recognize a famous curve from memory; record that limitation rather than claiming perfect blinding.

The reviewer answers: completed patterns in the last 20 sessions, none, uncertain, or invalid chart. Allow multiple completed events with per-event kind and selected completion offset. For completed labels, the reviewer declares the complete set they see within the target band; absence of another kind then has defined meaning. Do not ask for the predicted pattern specifically. Do not display another reviewer's label before submission.

## Labels and revisions

`record_review_label(queue, labels, entry)` accepts:

```text
entry: {
  case_id, reviewer_id, decision: "completed" | "none" | "uncertain" | "invalid",
  events: [{kind: "inverse_head_shoulders" | "cup_handle" | "head_shoulders_top",
            completion_offset: integer in [-19, 0]}],
  rationale: str up to 1000 characters,
  expected_revision: integer (0 for first label), revise: bool
}

labels: {
  study_id, queue_hash,
  entries: [{case_id, reviewer_id, reviewer_role, decision,
             events: [{kind, completion_offset, completion_date}], rationale,
             revision, supersedes_revision}]
}
```

The pure function maps offsets to private dates from the case; the browser need not receive calendar dates. `completed` requires one or more unique events; all other decisions require an empty event set. Anchor annotation is deferred. A future/outside-band offset, unknown ID/reviewer, reserved/locked card or changed study hash is rejected with `ValueError`, leaving input labels unchanged. Normalize event ordering before idempotency comparison. An identical submission returns the same logical labels; a different submission for the same case/reviewer requires `revise=true` and the exact current revision. Append a revision, preserving older provenance rather than overwriting it. No invalid/uncertain label becomes a negative.

Server persistence wraps the pure seam with operator/reviewer identity and receipt time in an append-only journal, plus atomic replacement of a materialized JSON view. Serialize submissions under one process lock and persist before reporting success. The standard library offers replacement semantics with `os.replace`; use a temporary file in the same directory. [Python os documentation](https://docs.python.org/3.11/library/os.html#os.replace). Labels and queue stay under ignored `private/cycle-2/`; a UI reset starts a separately identified study or archives labels, never edits the locked queue in place.

## Summary and matching

`summarize_review(queue, labels)` returns a **calibration-only, coordinator-private** report. Do not send it to the reviewer HTTP client: changing labels and observing aggregate match counts would reveal predictions. Reviewer HTTP responses contain only their own label history and progress. No public recognition/disagreement/stratum or other-reviewer answer release exists in this cycle.

```text
{
  study_id, queue_hash, phase: "calibration", holdout_locked: true,
  status: "pilot_annotation", trading_approval: false,
  coverage: {open_cards, by_reviewer: {reviewer_id: {
    labeled, completed, none, uncertain, invalid, unreviewed, role
  }}},
  consensus: {certain_cases, pending_cases, disagreement_cases,
              uncertain_cases, invalid_cases,
              agent_only_cases, human_supported_cases},
  recognition_agreement: {stratum: {kind: {
    certain_cases, predicted_events, labeled_events, matched_events,
    unmatched_prediction_events, unmatched_label_events,
    signed_completion_errors_sessions: [integer], availability_delays_sessions: [integer]
  }}},
  limitations: [fixed strings]
}
```

Use latest revisions only. Register **exactly two** distinct reviewer IDs with explicit roles. A case enters recognition denominators only when both latest decisions are certain (`completed` or `none`), decisions agree, and their full sorted `(kind, completion_offset)` sets agree **exactly**. Different offsets are disagreement, even if they would lie within the detector's three-session tolerance. Missing, uncertain, invalid or disputed cases stay unscored. There is no third vote, date reconciliation or individual-reviewer recognition score. Preserve both supporting IDs/roles in private provenance. Agent-only consensus is a pilot signal, not Gary's truth.

For detector matching, group by kind, sort by completion offset, and match each consensus event to the earliest unused eligible predicted event. Eligibility requires completion dates within three sessions and `prediction.available_at >= consensus_completion`; a signal emitted before the independent completion cannot count as a match. With v1's equal completion/availability, admissible delay is zero to three sessions. Keep signed completion errors and availability delays; report earlier predictions among unmatched events instead of hiding them. Each prediction/label can be matched once.

Separate random and enriched strata; dual-membership cards may appear in each descriptive stratum but must be explicitly identified as overlapping counts, never summed into a global accuracy. This small, correlated, purposive sample supports a pilot disagreement/error inventory. It does not establish universe precision/recall, cup sensitivity, efficacy or confidence intervals. Agent reviews are agent evidence, not Gary's ground truth. Keep unreviewed/uncertain/invalid cards out of certain-case denominators. No holdout score, card ID, prediction or chart is returned.

## Proposed implementation ownership and acceptance

- Review developer: `src/gary/review.py`, `tests/test_review.py`, synthetic `tests/fixtures/review*.json`, `docs/cycles/cycle-2-review-tdd.md`. Implement only the three approved pure seams; leave `src/gary/patterns.py` unchanged.
- Coordinator: `src/gary/review_preview.py` (cached-input adapter/CLI), `src/gary/preview.py` (existing localhost routes), `src/gary/static/review.html` (review UI), runtime/startup documentation, queue/label persistence and integrated cycle report.
- Independent QA: read-only public-seam and localhost checks, a small separately attributed pilot annotation subset, findings/rechecks. QA does not label itself Gary.
- Private outputs: `private/cycle-2/queue.json`, `labels.json`, `labels.journal.jsonl`, `source-manifest.json`; no vendor bars/labels are committed.

Observable TDD behaviors at the approved seams should cover seeded determinism and source-order invariance; exactly 180 clipped sessions; independent random sampling plus enrichment and dual-membership dedupe; source/time reservations and full-window overlap purge; split-boundary exclusions; visible-context prediction equivalence; sanitized cards with normalized values and no hidden fields; locked holdout rejection; all four decisions and multiple events; outside-band/unknown reviewer errors; idempotent submission and explicit revision; two-distinct-reviewer consensus and provenance; unreviewed/uncertain/invalid/disagreement denominator handling; one-to-one multi-event/date matching and early-availability nonmatches; and separate stratum summaries. Add one behavior at a time with observed red then green.

Localhost QA should inspect HTML and JSON for identity/prediction/holdout leakage, verify no future chart bars, exercise save/restart/retry/revision persistence, reject external-origin writes, ensure revisions cannot expose detector answers through score changes, and verify that review submissions leave detector hashes, coverage and portfolio state unchanged. Use the existing preview's origin/localhost conventions, vanilla SVG/canvas and local assets; no CDN, remote chart upload or external deployment is needed.
