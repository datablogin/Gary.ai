---
status: approved
---

# Comparison, detector improvement and Train more

Human request: “Let's just build from here. We need to add train more to the final application. Let's go forward from 2-3,” followed by shape-work then review-plan. This turn produces reviewed planning artifacts; it does not launch implementation. Research: [findings](../research/2026-10-11-train-more.md). Gates: [scorecard](../scorecards/2026-10-11-train-more.md). Assignments: [role briefs](../prompts/2026-10-11-train-more.md).

## Outcome and interpretation

Add an enduring local Train more workflow: collect a bounded new anonymous chart batch, resume/save judgments, seal the completed pass, compare it with the committed detector version, and request another round. Use the current completed human pass for development diagnostics immediately; do not wait for a new blind agent pass. Existing two-reviewer holdout reports keep their present rules and pending status. No agent judgments are fabricated.

Train more gathers evidence for rule improvement, rather than claiming automatic ML training. It never changes stock eligibility, allocation, paper state or broker behavior. Geometry changes are conditional on a reproducible, defensible requirement; otherwise deliver diagnostics/workflow with v1 retained. Candidates remain research-only and cannot silently replace the portfolio detector.

## Phases and ownership

0. **Reviewed approval and seams** — persist these four artifacts; three fresh non-author lenses critique them. Human approves the concrete scope and proposed added/versioned seams before tests or dispatch. No recurring automation.
1. **Locked-pass diagnostics** — evidence developer owns new src/gary/training_analysis.py and tests/test_training_analysis.py. Verify the completed pre-reveal human snapshot against its queue/view and trusted original release. Produce a coordinator-private per-case error inventory and aggregate descriptive event comparisons. Classify differences as matched, unmatched prediction, unmatched observation, uncertain/invalid, context-policy ambiguity or demonstrated rule violation. Do not infer a rule violation from disagreement alone or treat buy/hold prose as a completed pattern label. Save an immutable diagnostic under its input/protocol hash.
2. **Training-round core** — round developer owns new src/gary/training.py and tests/test_training.py. Implement deterministic admitted-source selection, one active round, explicit request idempotency, frozen prediction commitments, single-human labeling/revisions, completed snapshots, resume and round history. No filesystem/network in these pure seams. The coordinator freezes shared JSON contracts before parallel implementation; phase2 may start only after phase1 report contracts are fixed.
3. **Train more application integration** — coordinator owns new src/gary/training_preview.py, changes to preview.py, src/gary/static/review.html and src/gary/static/index.html, new src/gary/static/training.html, README/Makefile. Add Train more links from the portfolio/review pages and a local /learn hub with progress, round history, completed diagnostics and data-needed state. One POST /api/training/round creates/resumes; fixed-whitelist GET /api/training and /api/training/card and POST /api/training/label reuse assigned identity/origin and bounded JSON rules. Do not relax legacy routes. Buttons are explicit user actions, not background optimization.
4. **Conditional detector correction** — after inventory/adjudication proves a behavioral requirement, pattern developer owns new src/gary/patterns_v2.py and tests/test_patterns_v2.py. Use the existing detect_patterns(bars, as_of) seam: one observed failing regression, minimum correction, green, causal prefix/append invariance. Keep v1 bytes and prior releases intact. Register the candidate with source/parameter/input-context fingerprints in the coordinator-owned trusted registry. If no defensible change exists, record retain_v1 without a speculative v2.
5. **Independent QA and local delivery** — fresh engineering QA owns scripts/check_training_workflow.py and final QA evidence, and reviews/probes; it supplies no primary market judgments. Check public seams, actual UI, persistence/fault/concurrency behavior, snapshot integrity, exposure boundaries and version isolation. Fix failures through meaningful regressions, then make verify and push final code/evidence. Initial delivery is runnable Train more plus diagnostics; no required future human labels or fresh-source evaluation result is presumed complete.

## Confirmed logical seams and two proposed additions

| Public seam | Contract |
| --- | --- |
| analyze_training_pass(queue, completed_pass, reference) | Single-human development comparison. reference is an original frozen release or a committed training-round reference; validate variant, queue/view/pass/prediction/manifest/protocol binding. Original reference uses exact preserved180 inputs and predictions. Complete certain observations can enter descriptive matching; no independence/accuracy assertion. |
| training.build_review_queue(series, config) | New training-only schema/profile, one assigned human, bounded reproducible sampling with 180-session detector input and five-year overview. Own immutable IDs/hash and pre-label prediction/reference commitment; no legacy queue rewrite. |
| training.record_review_label(queue, labels, entry) | Existing judgment/event/revision semantics at a versioned namespace, with exact displayed token and generated view/input/version stamps. Single-human ownership; retry idempotency and full revision history. |
| training.summarize_review(queue, labels) | Progress while incomplete; after the sole human completes the round, seal/pass hash and explicitly personal development diagnostics. No synthetic second reviewer; old consensus summary untouched. |
| request_training_round(catalog, history, request) | Pure transition returning immutable round/history records or resume/needs_data/conflict. catalog contains validated retained series/classification/source receipts; request contains nonempty request_id and frozen config. Same id+payload is identical; conflicting reuse fails. Any existing incomplete round resumes instead of allocating another. |

The detector seam is already confirmed. The queue/label/summary logical seams were already confirmed; the new training namespace preserves those signatures. Only analyze_training_pass and request_training_round add test boundaries to confirm with implementation approval; all labels retain completed/none/uncertain/invalid and the same three kinds/final20 completion offsets. Future candidate/evaluation additions must use a separately confirmed contract rather than being hidden in this cycle.

## Comparison semantics

Reference inputs remain180 sessions for this cycle; five-year visual assistance is stamped and prominently identified in completed diagnostics. Matching is same-kind, one-to-one, earliest-unused predictions within three sessions of labeled completion, with availability no earlier than labeled completion and no later than the case cutoff, following the recorded v1 rule. Match only final20 target events. Sort events deterministically by kind/date; duplicate events are rejected. Zero-denominator fractions are null. Uncertain/invalid observations are unscored, with coverage/exclusion counts. Random and enriched strata retain memberships and separate descriptive denominators; an overlapping case is counted once in overall totals and once per applicable stratum.

The current pass was completed before identity reveal but uses wider visual history and previously exposed issuers. Bind the original-pass canonical payload hash to the trusted existing identity-reveal receipt’s gary_pass_snapshot_sha256 and queue_hash, plus its recorded revealed_at_utc. The frozen detector release is a prediction anchor, not a label chronology anchor. Validate all recorded receipt/snapshot relationships; a later revised payload cannot satisfy the original receipt. Existing journal timestamps/prefix commitments may corroborate chronology where available; do not retroactively invent a pre-reveal prefix commitment. Missing/conflicting chronology is explicitly reveal_timing_unknown and development-only. Explicit revisions after completion/reveal create a new development snapshot and cannot replace the preserved pass or be substituted into its report. Existing consensus reports remain pending if their required pass is absent. Do not call this an independent holdout or a strategy return result.

## Training selection and state

Before round allocation, the adapter bootstraps an immutable exposure manifest from every known prior queue/view, completed snapshot, reveal and source reservation. Canonical aliases and viewed/target intervals must be attributable to retained receipts; missing prior artifacts, unknown identity lineage or unverifiable intervals produce needs_data/admission exclusions, never an empty-ledger assumption. No legacy artifact is edited.

Default max12, up to6 random plus6 signal-enriched; deterministic seed/config and actual frames recorded. Deduplicate source/cutoff/window identity and retain memberships. Reject previously labeled final20 intervals and exact case duplicates across all prior calibration, exploration, assisted and training passes, including aliases through canonical catalog identity. Reject overlap with any active validation reservation’s canonical source or full context interval. Historical releases retain their original roles; after exposure their evidence may serve as development for a later version, and is never reclassified as unseen validation. Previously exposed broader history may be reused only as training with its overlap recorded.

Five-year interval is open-left (cutoff minus five calendar years, cutoff], Feb29 clamps to Feb28, minimum1200 sessions, first session within7 days, exact endpoint, no post-cutoff bars, complete finite ordered OHLCV and explicit source/timezone/price-basis/split metadata. New training rounds reject full-view reported splits. Reviewed source classification is required; missing cache/classification/coverage or too few distinct targets yields admitted smaller batch or needs_data, never fabricated bars or financial clearance. Data import/validation is an operator adapter; no automatic external fetch in this cycle.

Persist ready -> labeling -> complete, plus needs_data as a non-round outcome. Ready and labeling both count as the one active round. Same request/config/source/catalog/ledger inputs reproduce the same records; repeated click, concurrency and restart resume the single durable round. Different requests cannot create competing active rounds. A complete human pass is sealed automatically at acknowledged last save; an explicit post-completion revision appends a superseding development snapshot, never edits prior manifests. Completed rounds stay readable, and Train more creates the next separate round.

Adapter persistence uses a lock plus authoritative append-and-fsync events before acknowledgment and atomic materialized views. The authoritative transaction binds round/request/exposure allocation and queue commitment together; crash recovery cannot create a second round, lose acknowledged labels, or orphan an exposure reservation. Partial unacknowledged tails are ignored/archived without fabricating acknowledged work. All mutations reconstruct against retained source receipts, trusted version registry and sealed protocol, with exact view-token checks before writes. Missing/stale tokens never repair or alter journals. Runtime caching, if needed, must use verified full content fingerprints and invalidate on every input/protocol/source change, never timestamps alone.

## Candidate and validation separation

v1 patterns.py, review.py and evaluation.py, all old queues/releases/journals/snapshots and paper state remain unchanged. New modules and private/training own new behavior. The registry allowlists locally supported versions and verifies their executable/parameter/context fingerprints; requests cannot select arbitrary paths/modules or edit thresholds.

Current exposed evidence and future Train more batches are development data. Any candidate comparison on them is descriptive. A future validation reservation must use newly sourced, previously unexposed issuers (including aliases) and full context intervals disjoint from the complete exposure ledger. Record source receipts, candidate/source/parameter/policy commitments and predictions before display; deny its labels/results to tuning until evaluation is fixed. No fresh validation data are presumed available. Show needs_data and keep v1 research default; actual candidate promotion/evaluation is a later explicitly scoped step. Unavailable validation does not block delivery of diagnostics and calibration UI.

## Runnable gates and limits

- Before tests: human-approved contracts and shared synthetic fixture schemas. Tests exercise public seams, one red -> minimum green slice at a time; no real labels invented.
- During implementation: uv run pytest tests/test_training_analysis.py tests/test_training.py -q; conditional tests/test_patterns_v2.py; literals for matching boundaries, uncertain/invalid exclusions, changed-context interpretation, incomplete summaries, stamped retries/revisions, request conflicts, resume/round caps/selection, alias/exposure/target overlap and missing-source outcomes.
- Final: make verify (all existing386 tests plus additions), node --check on extracted UI scripts; uv run python scripts/check_training_workflow.py against an isolated temporary store for HTTP save/round race/crash/partial-tail/reload/version/source tampering; actual-browser Train more -> round -> completion -> report -> another round. Use synthetic QA labels only in isolated copies; actual current user labels are not rewritten or interpreted by engineering QA.
- Preservation: capture before/after hashes of every old source, queue, release, journal, materialized label, completed-pass/reveal and paper artifact. Keep comparison scores/label findings and provider data out of git/public docs. Local only; no brokerage, MCP hosting, external deployment, subscriptions, fundamentals build, investment-policy change or Sharpe/backtest claim.

Rollback: stop localhost or disable the new /learn route through a new commit; retain every training journal, snapshot, source receipt and exposure record. Restore the prior research-version selection explicitly without changing any completed release/report. Legacy review stays available; assisted-view exposure keeps the original pass read-only. Candidate failure or missing data leaves v1 available and no paper transaction is triggered.

## Literal acceptance cases to freeze before tests

| Case | Expected behavior |
| --- | --- |
| Label completion -4; prediction completion/availability -1 | Same-kind single event matches at the inclusive +3 boundary. |
| Label -4; prediction completion/availability 0 | No match: four-session completion error. |
| Label 0; prediction completion/availability -1 | No match: availability predates the human completion despite close dates. |
| One certain matched case with random+enriched membership | One case/event in overall totals and one in each stratum; no double overall count. |
| Uncertain or invalid case with detector events | Entire case unscored; no negative label or false-positive count. Zero scored denominators yield null fractions. |
| Otherwise valid context with1199/1200 sessions | Reject1199; admit1200 under the other source/interval gates. |
| Otherwise valid context starts anniversary+7/+8 days | Admit+7; reject+8. |
| Cutoff2024-02-29 | Anniversary2019-02-28; exclude the anniversary bar itself; no bars after cutoff. |
| Later revised pass vs original reveal receipt | Cannot replace/satisfy the original committed pass; original report retained, new diagnostic snapshot separately attributed. |
| Missing legacy queue/alias/target or full-view interval evidence | Fail admission conservatively with needs_data/exclusions; never silently initialize empty exposure history. |
| Ready/labeling round A; request B | Resume A; no second active round or extra exposure allocation. |
| Same request ID, changed payload | Conflict without mutation. Identical retry reproduces/resumes existing records. |
| Bad token after acknowledged revision and partial journal tail | Reject before repair, cache rewrite, label append or exposure change. |

These are independent specification examples for the already planned seams, not test code or current real-judgment findings.

## Review (2026-10-11)

Verdict: **SHIP**. Three fresh, read-only, non-author lenses reviewed all four artifacts and rechecked the contract clarifications once. No blocking finding; all five advisories resolved. Status is reviewed, not approved. Human approval of this concrete plan and the two additional analysis/request test boundaries is next, followed by dispatch. Existing queue/label/summary/detector logical approvals remain in force.

| Lens | Finding and resolution | Final verdict |
| --- | --- | --- |
| Feasibility | QA now solely owns scripts/check_training_workflow.py with coordinator integration; static paths are repository-rooted. Separate single-human namespace fits frozen-module constraints. | SHIP, no remaining findings |
| Verifiability | Added literal matching/admission/state outcomes; original completed-pass hash must match the existing reveal receipt rather than a later revision or detector release alone. No retrospective chronology commitment is invented. | SHIP, no remaining findings |
| Scope/risk | Made conservative legacy exposure/alias/interval bootstrap explicit; missing evidence fails admission. Distinguished active validation reservations from historical exposed releases without rewriting old roles. | SHIP, no remaining findings |

Planning artifacts were committed/pushed before review. This reviewed revision is likewise persisted to main and remote-verified. No product code, tests, primary judgments or prior private artifacts changed during shaping/review.

## Human approval (2026-10-11)

The user explicitly replied approved to the reviewed plan and its two additional test interfaces, then invoked dispatch-wave. Record that human approval in frontmatter. The existing detector/queue/label/summary approvals remain in force. This request selects dispatch-wave brief mode; assignments and harness have not yet been explicitly selected from a dispatch manifest. No implementation was launched while recording approval.
