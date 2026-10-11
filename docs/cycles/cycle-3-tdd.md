# Cycle 3 review/evaluation TDD

Approved boundaries: `build_review_queue`, `record_review_label`, `summarize_review`, `freeze_evaluation`, and `evaluate_detector`. User confirmed the three cycle-3 additions before tests. Controls are synthetic; no real private labels or heldout predictions were inspected. Original detector source is retained unchanged.

Each row records a sequential vertical slice: write one public behavior, run the selector and observe red, implement the minimum behavior, rerun the selector and observe green. No internal collaborator is mocked.

| Slice / exact pytest selector | Observed red | Observed green |
| --- | --- | --- |
| `tests/test_review.py::test_five_year_profile_has_three_full_anonymous_daily_contexts` | 1 failed: original config rejects the new profile | 1 passed: three normalized variable-length contexts with private requested bounds |
| `tests/test_review.py::test_five_year_profile_refuses_incomplete_or_ineligible_context` | 5 failed, 1 passed: short/late/split/original-source/missing-cutoff contexts accepted | 6 passed: strict complete-lookback and disjoint-source checks |
| `tests/test_review.py::test_five_year_labels_match_final_event_with_dynamic_offsets_and_exploration_status` | 1 failed: fixed −179 matching origin misses an event at the long card's final session | 1 passed: actual-length matching and explicit exploratory/convenience summary |
| `tests/test_evaluation.py::test_complete_calibration_freezes_deterministic_holdout_without_mutating_inputs` | 1 failed: approved evaluation module absent | 1 passed: deterministic derivative 180-session holdout, snapshots/manifests and input immutability |
| `tests/test_evaluation.py::test_freeze_refuses_incomplete_or_unsupported_calibration` | 4 failed: incomplete/unsupported/exploration/empty calibration accepted | 4 passed: original complete two-pass calibration and supported v1 required |
| `tests/test_review.py::test_five_year_public_card_tampering_is_rejected_even_with_recomputed_hash` | 2 failed: forged public prices accepted at label and summary boundaries with empty history | 2 passed: public card must reproduce the committed raw context |
| `tests/test_evaluation.py::test_released_holdout_accepts_own_labels_but_rejects_original_calibration_ids` | 1 failed: derivative profile unsupported | 1 passed: derivative labels/retries accepted; original calibration ID remains unavailable |
| `tests/test_evaluation.py::test_partial_holdout_reports_progress_with_null_recognition_until_two_full_passes` | 1 failed: confirmed evaluate interface absent | 1 passed: one full pass has progress, null recognition and snapshot provenance |
| `tests/test_evaluation.py::test_freeze_rejects_forged_original_evidence_even_with_recomputed_queue_hash` | 6 failed: forged detector/predictions/context/dates/source/ID accepted | 6 passed: trusted detector manifest and raw-context reproduction before exposure |
| `tests/test_review.py::test_new_profile_summary_validates_private_context_and_structure_before_first_label` | 6 failed: malformed dates/predictions/card sets/schema/manifest/lock accepted with empty history | 6 passed: profile structure, context and prediction reproduction validated before labels |
| `tests/test_evaluation.py::test_released_profile_rejects_forged_provenance_or_calibration_cards` | 4 failed: mismatched parent/release or calibration/wrong-split card accepted | 4 passed: derivative provenance and source/time reservations enforced |
| `tests/test_evaluation.py::test_evaluation_rejects_recomputed_release_commitments_that_disagree_with_parent_or_trusted_sources` | 6 failed: coherently rehashed altered predictions/context/snapshot/evaluator/policy accepted | 6 passed: reconstruct the expected release from parent contexts and trusted executable/protocol manifests |
| `tests/test_evaluation.py::test_complete_holdout_reports_separate_time_symbol_and_random_enriched_event_counts` | 1 failed: holdout results flatten source/time partitions | 1 passed: separate source/time × random/enriched counts, timing and explicit overlap |
| `tests/test_evaluation.py::test_released_summary_identifies_holdout_and_hides_partial_recognition` | 1 failed: derivative summary calls itself locked calibration | 1 passed: holdout phase/lock and partial-score suppression at the existing summary boundary |
| `tests/test_evaluation.py::test_freeze_requires_original_complete_case_partition_and_disjoint_exploration_sources` | 5 failed: omitted/duplicate calibration cards, wrong source/time partitions or exploration overlap accepted | 5 passed: complete original partition and disjoint source audit before exposure |
| `tests/test_review.py::test_five_year_profile_cannot_omit_a_declared_source_after_rehashing` | 1 failed: a coherently rehashed queue could omit a declared exploration source | 1 passed: exactly one context for each declared source required |

Commands use `uv run pytest <selector> -q`. Consolidated verification is recorded after the final slice.

## Final verification

- `uv run pytest -q` → **311 passed**. All **264 legacy tests** remain green; this cycle adds **47 cases across 16 sequential red/green slices**.
- `uv run pytest tests/test_review.py tests/test_evaluation.py -q` → **79 passed** (49 review, 30 evaluation).
- `git diff --check` → exit 0, no whitespace errors.
- Independent QA reported passing synthetic core, five-year, persistence, HTTP and restart probes, including coherently recomputed release commitments and trusted source drift. The coordinator owns the integrated evidence and actual release.

Final executable SHA-256 values, before the coordinator's actual freeze:

| Executable | SHA-256 |
| --- | --- |
| Original `patterns.py` (unchanged) | `76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a` |
| `review.py` | `aec0b6a02a80da2fd46cbe1a2b58b87382e31f6fd108b9071cfa017042fd3d19` |
| `evaluation.py` | `1f2b9d04aec3af8a39731af2d2d6d9f1c6cb522b3313b9570a1cd3f7290a9757` |

The developer made no commits, git mutations, original private-data changes, real label observations or portfolio writes. No detector tuning was justified or introduced. Five-year exploration is a distinct convenience profile; original 180-session prediction contexts remain the evaluation basis. Missing human holdout labels must remain pending, with null recognition until both complete passes exist. Any later executable edit requires a new freeze rather than reuse of these manifests.
