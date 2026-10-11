# Five-year-assisted holdout: independent QA

Checked October 11, 2026; successful independent runs completed on the retained context view. This review was independent of the context module and adapter/UI authors. Runnable evidence is [check_holdout_context.py](../../scripts/check_holdout_context.py), invoked as:

```sh
uv run python scripts/check_holdout_context.py
uv run python -m py_compile scripts/check_holdout_context.py
```

Both commands passed. The QA script supports `--study-dir` for a cycle-3 root and `--port` for its isolated HTTP child, defaulting to the actual cycle-3 study and port 4176. It never writes to the configured study. All invented observations and persistence/recovery mutations occur in a disposable copied study, removed when the run ends. No source collector, external data fetch, portfolio run/reset, real primary-label write, or git operation was performed by this QA task.

## Real retained sources and presentation

The public `load_release` validates the original release through its existing frozen commitments. `cycle3_study("holdout")` selects the separate assisted queue and reconstructs it from that validated release and retained raw sources. QA independently decodes the eight source responses, checks manifest SHA-256 and byte lengths, identity/type/timezone, array completeness, ordered timestamps and session dates, valid OHLCV, and absence of post-fetch session dates. It then calls the approved context queue seam and requires equality with the runtime queue.

All 13 contexts exactly equal the open-left historical interval `(cutoff minus five calendar years, cutoff]`. Returned counts range from **1,254 to 1,259 sessions**; every context starts within seven days of its anniversary and reaches its exact original cutoff. Every final 180-session date/OHLCV window and original normalized detail card is unchanged. Both chart endpoints have relative offset zero, and both target bands remain the final 20 sessions. Overview prices use their own first-close base of 100; volumes use their own median base. Exactly **three contexts** carry the expected anonymous relative-offset markers derived from retained reported split events.

Public queue/card projections match exact field whitelists. They contain normalized OHLCV and relative session offsets, an opaque case identifier and queue-bound view token; they expose no source identity, calendar dates, detector answers, sampling memberships or other-reviewer observations. The original queue order and all detail payloads remain equal to the released parent. The context queue hash differs from the parent and binds its supplemental representation.

These checks establish retained-source and presentation consistency. They do not certify exchange-calendar completeness, provider adjustment correctness, point-in-time availability, recognition accuracy or investment performance.

## Public seams, anchors and isolated HTTP

The synthetic fixture exercises the three approved queue/label/summary seams. Checks passed for input immutability, identical retry behavior, queue-derived protocol/overview provenance despite forged client fields, other-reviewer hiding, complete changed-view interpretation and withholding recognition/consensus while context passes remain incomplete. The summary identifies `phase=holdout_context`, `original_holdout_comparable=false`, and the frozen reference input of 180 sessions. These are fabricated protocol observations, with no interpretation of real primary labels or predictions.

The temporary copy reproduced a same-input build without changing any existing study, source, exposure or label bytes. A coherently changed early historical raw bar, normalized overview, window hash and outer queue hash passed internal consistency but was rejected by the runtime's retained-source reconstruction. Altered frozen evaluator-source and protocol commitments, with a recomputed outer release hash, were rejected by the existing release validation. The locally retained source manifest/raw files and frozen executable sources remain the trust boundary; no additional signing system is assumed.

The production HTTP entrypoint ran against the disposable study, bound to the assigned human reviewer. All **29 requests** passed their expected behavior:

- Missing, wrong and original-view tokens were rejected before journal or materialized-view changes, both before the first save and after revisions/cache loss/an incomplete journal tail. Rejection did not repair the tail or recreate the missing cache.
- Valid save, identical retry, explicit revision and rejection of an implicit conflicting revision preserved the expected history.
- A deleted materialized label view recovered from the journal. An incomplete unacknowledged journal tail survived a process restart without becoming a label; the next valid revision archived the tail and retained all acknowledged revisions.
- A foreign reviewer, reviewer query override, foreign origin and foreign host were rejected without writes. Private summary/report/queue/file routes and unregistered study names returned 404.
- The preserved original view rejected writes. After loss of the assisted queue, retained exposure still made the original fallback read-only, and its journal remained unchanged.

Adapter review found that the initial queue-loss fallback could reopen the original pass after context exposure. The coordinator corrected that behavior by retaining read-only status from `exposure.json`; the independent HTTP rollback probe passed after the correction. An initial probe attempt stopped at a 20-second client timeout during restart recovery. The final successful independent run used a bounded 45-second limit and measured a maximum request duration of **3.105 seconds**. No real study state changed in any attempt.

## Preservation and remaining gate

All **44 files** in the private preservation baseline matched their original SHA-256 before and after the successful run. The baseline covers original release/queues, prior journals/materialized labels/evidence, paper preview state, and frozen `review.py`, `evaluation.py` and `patterns.py`. The actual new context study's source, queue, exposure and any label bytes also matched their pre-QA hashes. Original observation artifacts were checked only as bytes; no case-specific mapping or primary observation is published here.

The independent script and syntax gate are complete, with no remaining functional blocker found. The coordinator owns the full repository verification and actual-browser overview/detail/target-control gate; this record does not substitute HTTP projection evidence for that visual check.
