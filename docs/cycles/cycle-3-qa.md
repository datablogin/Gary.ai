# Cycle 3 independent QA

Date: 2026-10-10, America/Chicago. Verdict: **PASS**, with no remaining blocking functional findings on the final sources below.

The QA role did not author product code or repository tests, edit primary market judgments, commit, or push. Public-seam and HTTP controls used wholly synthetic data under ignored `private/cycle-3/qa/`. Original private artifacts were compared by SHA-256 only; their label contents and real held-out predictions were not interpreted. This report certifies workflow behavior, not market recognition accuracy or investment performance.

## Verified executable provenance

| File | SHA-256 at final verification |
| --- | --- |
| `src/gary/patterns.py` | `76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a` |
| `src/gary/review.py` | `aec0b6a02a80da2fd46cbe1a2b58b87382e31f6fd108b9071cfa017042fd3d19` |
| `src/gary/evaluation.py` | `1f2b9d04aec3af8a39731af2d2d6d9f1c6cb522b3313b9570a1cd3f7290a9757` |

`patterns.py` retains its original digest. The hash-only preservation guard checked eight paths covering the original detector, cycle-2 study/config/label artifacts, copied baseline artifacts, and paper state. All remained unchanged, including absence where a file had not existed at capture.

## Exact commands and results

Run from `/Users/robertwelborn/Projects/Gary.ai`. The independent probe scripts and generated controls remain machine-local, Git-ignored QA evidence. The committed pytest suite remains runnable without private market data.

| Command | Final result |
| --- | --- |
| `make verify` | **311 passed**; `git diff --check` passed |
| `uv run python private/cycle-3/qa/core_probe.py` | Passed freeze completeness/determinism, input preservation, partial-score gating, snapshot provenance, split/stratum reporting, null denominators, one-to-one matching, uncertain/invalid/disputed exclusions, coherent release tampering, and executable drift |
| `uv run python private/cycle-3/qa/five_year_probe.py` | Passed calendar bounds, relative offsets, 1,305-session synthetic contexts, clipping/normalization, malformed/missing/split/original-source refusal, exploration provenance, long-context completion dates, and recomputed-hash card refusal |
| `uv run python private/cycle-3/qa/persistence_probe.py` | Passed own-label projection, locked-case refusal, retry idempotence, materialized-view loss, torn-journal recovery, explicit revisions, stale-write refusal, and immutable synthetic queue |
| `uv run python private/cycle-3/qa/http_probe.py` | Passed release-before-exposure, immutable rebuild, response whitelists, identity/path/private-route refusal, frozen-calibration write refusal, save/retry/revision/cache-loss recovery, live release revalidation, recomputed-hash card refusal, rehashed malformed-source refusal, process restart, paper/calibration/release immutability, and preserved report revisions |
| `uv run python private/cycle-3/qa/gate_regressions.py private/cycle-3/qa/http-x2x_9b93/study --fixed` | All three regression requests returned **400**, exposed zero cards where applicable, and omitted source identity |
| `uv run python private/cycle-3/qa/state_guard.py check` | `unchanged`, eight checked paths, zero changed paths |
| `shasum -a 256 src/gary/patterns.py src/gary/review.py src/gary/evaluation.py` | Matched the table above |

Final isolated artifacts: `private/cycle-3/qa/core-a0pq8ao1/`, `private/cycle-3/qa/persistence-z8bzdyku/`, and `private/cycle-3/qa/http-x2x_9b93/`.

The tampering probe recomputed `release_id`, derived study identity/references, `queue_hash`, and `release_hash` after altering prediction, context, evaluator, protocol, or parent evidence. Rejection therefore did not depend solely on stale outer checksums. Source-drift probes copied only public executable files into isolated packages, changed `patterns.py`, `review.py`, or `evaluation.py`, and used fresh interpreters to verify rejection of the original commitment. No live source file was changed by QA.

Complete synthetic holdout passes exercised descriptive event counts and separate `time_holdout`/`symbol_holdout`, random/enriched strata. Partial passes returned `recognition_agreement=null`. One prediction matched at most one of two consensus events; uncertainty, invalidity, and exact-offset disagreement were excluded. Pending reports created no scored holdout snapshot. Two later completed report revisions retained both immutable snapshots.

## Observed failures and corrections

Independent review identified three wrapper defects. QA reproduced them before correction with:

```sh
uv run python private/cycle-3/qa/gate_regressions.py private/cycle-3/qa/http-lr6stalp/study
```

| Trigger | Observed before correction | Verified after correction |
| --- | --- | --- |
| Legacy server pointed at a synthetic five-year queue | HTTP 200; three cards served without a release gate | HTTP 400; zero cards |
| Cycle-3 calibration fallback supplied a five-year profile while release was absent | HTTP 200; three cards served | HTTP 400; zero cards |
| Synthetic raw-source bytes failed their manifest hash | HTTP 400 error named the source symbol | HTTP 400 generic evidence-verification error |

The coordinator restricted legacy/fallback admission to the original profile and sanitized reviewer-facing study-load errors. Runtime five-year reads also rebuild the expected queue from retained raw bytes and stored config before exposing cards, including before the first label. QA verified refusal after public-card tampering with a recomputed queue hash and after an unequal quote array with recomputed raw hash/byte count.

## Browser and viewport verification

A QA-only Chrome tab used the final synthetic fixture, never a real study. The isolated server ran from `private/cycle-3/qa/http-x2x_9b93/` with:

```sh
PYTHONPATH=/Users/robertwelborn/Projects/Gary.ai/src /Users/robertwelborn/Projects/Gary.ai/.venv/bin/python -m gary.preview --cycle-3 --cycle-3-dir /Users/robertwelborn/Projects/Gary.ai/private/cycle-3/qa/http-x2x_9b93/study --port 4183 --reviewer qa-human
```

CUA screenshots and DOM inspection verified the existing **1448×814** viewport and a temporary **665×814** responsive viewport. In both, `document.documentElement.scrollWidth` equaled `window.innerWidth`. The overview close path contained **1,305** points and the recent-session detail contained **180** points. Detail ticks included −179, −120, −60, −19, and 0, with the final band marked `REVIEW BAND`. The narrower view retained the study selector, assigned identity, progress, overview, and detail.

The observed UI actions used `selectOption('completed')`, `selectOption('cup_handle')`, `selectOption('0')`, rationale fill, and the Save button. The synthetic submission returned HTTP 200, showed revision 1, and advanced own progress to 1/3. Selecting none, checking the explicit revision box, and saving returned HTTP 200/revision 2. Reload and study navigation retained revision 2. Completed calibration disabled judgment, rationale, and Save controls while leaving Study enabled.

An earlier synthetic browser fixture became stale when evaluator code changed during development; a save was refused before acknowledgment. A fresh fixture frozen against the final digests above passed the full save/revision/reload sequence. This independently exercised runtime scoring-drift refusal.

The temporary viewport override was reset, the QA-only tab closed, and the isolated port-4183 process stopped. The hash-only guard still reported all eight original paths unchanged afterward.

No real recognition conclusion is established by these synthetic checks. Real holdout metrics require the separately completed registered review passes and remain coordinator-private.
