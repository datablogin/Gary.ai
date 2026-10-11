# Cycle 2 review TDD evidence

Approved seams: `build_review_queue`, `record_review_label`, `summarize_review`. Frozen parameters and JSON contracts were reviewed and persisted before tests. Fixtures below are synthetic; market accuracy and investment efficacy are not inferred. No existing detector changes.

Commands use `uv run pytest tests/test_review.py::<selector> -q`.

| Behavior selector | Observed red | Observed green |
| --- | --- | --- |
| `test_queue_opens_two_normalized_fixed_length_random_calibration_cards` | 1 failed: callable stub exposed zero cards | 1 passed after seeded fixed-window/normalized calibration builder |
| `test_reserved_sources_and_full_context_time_holdout_stay_sealed` | 1 failed: reserved source exposed calibration cards | 1 passed after whole-source reservation and full-context temporal purge |
| `test_known_split_intersections_are_never_open_or_locked_cases` | 1 failed: selected card intersected reported split | 1 passed after inclusive split-window exclusion |
| `test_enrichment_retains_predictions_from_exact_visible_context` | 1 failed: no enriched case | 1 passed after frozen detector enrichment and same-visible-context predictions |
| `test_unsupported_window_change_fails_instead_of_mislabeling_cards` | 1 failed: changed window ignored | 1 passed after frozen config validation |
| `test_absent_corporate_action_metadata_has_explicit_error` | 1 failed: leaked KeyError | 1 passed after explicit source/provenance validation |
| `test_completed_label_records_private_date_role_and_revision_without_mutation` | 1 failed: no recorded label | 1 passed after immutable date/role-attributed recording |
| `test_identical_label_retry_is_idempotent` | 1 failed: duplicate label appended | 1 passed after identical-content retry handling |
| `test_conflicting_label_needs_explicit_current_revision_and_keeps_trail` | 1 failed: conflict silently accepted | 1 passed after explicit revision and append-only supersession |
| `test_label_validation_blocks_ineligible_or_ambiguous_submission` | 4 failed: holdout/future/ambiguous entries accepted; unknown reviewer leaked KeyError | 4 passed after label eligibility/event validation |
| `test_changed_queue_or_wrong_label_study_is_rejected` | 1 failed: wrong queue hash accepted | 1 passed after queue/label provenance integrity checks |
| `test_unreviewed_cards_are_pending_with_no_recognition_denominator` | 1 failed: no pending report | 1 passed after calibration-only coverage/report initialization |
| `test_two_exact_none_labels_create_one_agent_consensus_case` | 1 failed: unanimous observations stayed pending | 1 passed after exact two-reviewer consensus/provenance |
| `test_consensus_detected_event_matches_once_in_its_own_stratum` | 1 failed: matched counts remained zero | 1 passed after one-to-one per-kind stratum matching |
| `test_detector_cannot_match_an_independently_later_completion` | 1 failed: earlier available signal counted as match | 1 passed after nonnegative independent-completion availability constraint |
| `test_nonstring_submission_identity_has_public_validation_error` | 2 failed: list/dict IDs leaked TypeError | 2 passed after explicit identity types |
| `test_all_source_dates_are_validated_even_beyond_last_listed_date` | 1 failed: future first row escaped whole-source validation | 1 passed after canonical dates/full-source cutoff validation |
| `test_malformed_reserved_source_config_uses_public_error` | 1 failed: malformed reserved-source list leaked TypeError | 1 passed after type-safe config handling |
| `test_random_enriched_duplicate_is_one_card_with_explicit_overlap_count` | 1 failed: overlap count absent despite correct merged card | 1 passed after explicit coordinator-private overlap count |

Consensus status is mutually exclusive, with invalid → uncertain → pending → disagreement → certain precedence. Even one submitted uncertain/invalid observation stays unscored. Completion/date matching is separate from exact reviewer consensus. Only coordinator-private reports expose recognition counts; reviewer HTTP projection belongs to the coordinator.

## Verification and handoff

The table records **19 observed red/green behavior selectors, 23 test cases** including parameterized validation cases. Nine additional characterization cases passed when introduced: deterministic/source-order rebuilding and input immutability, strict public-card projection, uncertain/invalid exclusion, exact date disagreement, one-prediction/two-label matching, latest-revision consensus removal, changed-queue rejection, and zero-volume display handling. They are verification controls, not additional claimed red/green cycles.

`uv run pytest tests/test_review.py -q` → **32 passed**. The coordinator separately reported **264 integrated tests passed** and an unchanged persisted market-queue hash after rebuilding. The module is 325 lines and depends only on the standard library and the existing approved detector. `git diff --check` found no whitespace errors.

No detector edit: `src/gary/patterns.py` SHA-256 remains `76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a`. No developer writes to the live queue or labels, portfolio, HTTP server or adapter were made. The coordinator owns those paths and independent QA/rechecks. Any fictional labels used to exercise localhost save/revision controls are workflow QA, not Gary's annotations or market ground truth. Agent-only pilot consensus cannot substantiate real-chart accuracy or investment efficacy.
