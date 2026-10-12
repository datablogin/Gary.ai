# Diagnostics TDD evidence

Status: A1 worker complete after the October12 resume; independent supervisor replay remains the dependency gate. This document contains synthetic engineering evidence only. Actual observations, comparisons and case identities remain under ignored private/training/diagnostics.

The developer reported vertical observed red/green slices for the missing analysis seam, uncertain/invalid exclusions, trusted raw180/reference bindings, derived single-human stamps, pending coverage-only behavior and private difference categories. The supervisor independently ran the saved test file at pause:29 passed in1.65s. Literal inclusive+3, rejected+4, never-early availability and overlapping strata controls are included. The first original-release/receipt fixture is green.

## Resumed vertical slices

All tests use the approved analyze_training_pass(queue, completed_pass, reference) seam and synthetic fixtures. No internal collaborator is mocked.

| Behavior | Observed red | Minimum change and observed green |
| --- | --- | --- |
| Missing/null original receipt | Two cases raised integrity errors rather than the contract's unknown chronology outcome. | Permit the missing receipt field or null value; retain validated release/view/history and return reveal_timing_unknown with no independence claim. Two cases green; full analysis suite31 passed at this point. |
| Boolean superseded original revision | Corrupt supersedes_revision=True was accepted as integer1. | Reject non-integer superseded revisions before frozen history validation. Targeted case green; full analysis suite49 passed at this point. |
| Detector input stamp type | A training label stamped180.0 was accepted. | Require the generated reference_detector_input_sessions stamp to be an integer. Targeted case green. |
| Coherently hashed non-list order | A map replacing the ordered case list was accepted at the analysis seam. | Require a list before queue integrity checks. Targeted case green. An initial fixture KeyError was corrected before observing this behavioral red. |

Existing frozen validation already passed the newly added controls for coherently rehashed detector source/parameter/evaluator/prediction/protocol changes and conflicting present receipt schema/queue/pass/time/chart evidence. These were green regression controls, not claimed red/green implementation slices. Explicit later revisions fail against the original receipt, obtain a separate development report without that receipt, and leave the original report reproducible. An incomplete pass with missing chronology exposes coverage only.

## Commands and results

The shell did not include uv in PATH; the existing executable was used directly. No installation occurred.

```sh
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training_analysis.py -q -k without_receipt
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training_analysis.py -q -k boolean_superseded
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training_analysis.py -q -k input_session_stamp_requires
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training_analysis.py -q -k case_order_requires
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training_analysis.py tests/test_context_review.py tests/test_review.py tests/test_evaluation.py -q
```

The first four commands each had the observed behavioral red above, followed by a green rerun after its minimum change. The compatibility command passed206 tests, including52 analysis cases. The manifest's literal private replay command passed after generating the immutable input bundle, report and separate error inventory. Every original preserved received-byte fingerprint matched the430-file baseline. git diff --check passed. These are worker verification results; the coordinator independently reruns the A1 release commands before A2.

## Reference recipes for the next owner

The original-release input bundle uses the actual cycle3_study("holdout") queue, preserved completed snapshot selected by the existing reveal receipt, load_release(), and the original calibration queue as parent_queue. The original release is reproduced with freeze_evaluation against the trusted frozen executables, and its holdout parent reconciles with the assisted queue and exact180 tails. Missing/null receipt yields unknown timing; present contradictory evidence fails. A reference object cannot authenticate its own external origin: the adapter and supervisor must verify retained file/source receipts, canonical snapshot bindings and executable bytes.

The training-round variant is exactly {kind: "training_round", commitment: queue.sealed.reference}. The sealed reference contains schema_version=training-round-reference-v1, the fixed target20/tolerance3/never-early protocol, trusted detector_manifest, context_sessions=180 and visual_context_years=5. prediction_hash is the canonical hash of {case_id: case.predictions}; inputs_hash is the canonical hash of {case_id: hash(case.raw_window)}. commitment_hash hashes the reference excluding itself. queue_hash hashes the entire queue excluding itself; there is no circular queue_hash in the reference. Every raw_window is exactly180 bars and must equal the raw_context's final180 bars; cards reproduce both detail and overview.

Training history has one assigned human with sequential integer revisions and integer/null supersedes_revision. Every row carries generated view_protocol=training-five-year-v1, exact queue_hash as view_token, overview_hash, reference_hash=commitment_hash, trusted detector_version and integer reference_detector_input_sessions=180. Pending reports have coverage and null overall/by_stratum/inventory. Complete reports are deterministic, carry canonical report_hash excluding itself, and classify descriptive differences without turning disagreement or prose into a demonstrated requirement.

No primary findings, scores, label distributions or company-case mapping are recorded here. No old two-reviewer summary, frozen executable, source, snapshot, receipt, later live label or paper state was changed. A1 stops before round implementation, candidate tuning and dependent launch. Full instructions remain in docs/dispatch/2026-10-11-train-more.md.
