# Train more independent engineering QA

A5 / `train-more-qa`, October 12, 2026. The independent worker read the approved dispatch preamble, plan, research, scorecard, role briefs, CONTEXT.md, contracts and integration evidence; no applicable AGENTS.md/CLAUDE.md appeared. The TDD skill and its tests/mocking guidance were read. Ownership remained `scripts/check_training_workflow.py` and this evidence. Product corrections, git and delivery remained with the coordinator.

The first probe ran against integrated SHA `6921cf190d22f57c6e6bdb6089911fbb4ee3a279`. Final HTTP verification ran against `f28d08402ea72413fd0a70ea6d0c51bf77959a1a`, containing the coordinator's minimal data-needed reload correction. The coordinator reported this SHA equal to public remote main; remote equality is a coordinator delivery gate, not inferred from worker self-report.

## Verified

Literal commands, using existing dependencies only:

```sh
.venv/bin/python scripts/check_training_workflow.py --port 4177
.venv/bin/python -m py_compile scripts/check_training_workflow.py
git diff --check
git rev-parse HEAD
```

The workflow script exited 0 with all seven probe groups verified. It owns and closes every child server, refuses an occupied port and creates all synthetic sources, labels, stores, package copies and logs beneath one disposable temporary root. It never calls source fetching, paper run/reset, brokerage or a production label mutation. Tests exercise the approved HTTP and pure domain seams; OS `fsync` is the only injected crash boundary.

| Probe | Observed behavior |
| --- | --- |
| HTTP workflow | Both application entry points link to `/learn`. Explicit request, retry and six concurrent new requests retain one round. Two simultaneous identical saves retain one label revision. Anonymous cards contain literal 1305-session five-year overviews and separate exact 180-session detail, relative offsets and final 20-session targets. Incomplete diagnostics are null; private source/reference/receipt fields and other identities remain hidden. Identity, host/origin, token, path, version override and oversized request guards reject without store-byte changes. |
| Admission | Missing exposure completeness, alias evidence, nonterminal canonical aliases, missing target/view/reservation provenance, labeled target reuse, active reserved issuers and full-context reservation overlap yield needs_data without allocation. Broader prior view overlap remains explicitly development exposure. Conflicting reuse of a request ID rejects without mutating history. |
| Subsequent round | Seven flat synthetic sources yield six random cases, then one separate unused case after completion. Earlier request retries retain their original round, current hub/restart resumes the sole new active round, and earlier completed reports/passes remain byte-identical. |
| Tampering | Coherent bootstrap/header self-hashes cannot substitute catalog bars or manifests for independently retained raw/executable anchors. Altered raw bytes, missing receipts and coherent queue/reference protocol sidecars fail closed without writes. A warmed cache also rejects a same-length raw modification with its original filesystem timestamp restored. Disposable copies with changed patterns.py, review.py or evaluation.py bytes are rejected; production executables are never altered. |
| Durability | Owned request/label child processes exit immediately before and immediately after journal fsync, before an HTTP acknowledgment. Retry/restart retains one allocation and one label/snapshot. A later abrupt process kill retains acknowledged revisions. Cache deletion plus a partial journal tail retains every acknowledged label; missing/stale tokens leave journal/tail/cache bytes unchanged. A valid retry archives the interrupted tail and reconstructs the immutable earlier passes/reports. |
| Legacy isolation | Actual legacy artifacts are inspected only through hashes and public structural projections. The preserved original holdout remains read-only, its attempted synthetic save receives 403, and its public progress/consensus projection remains identical after a disposable training completion. All 430 prior received-byte fingerprints match, including frozen executables and paper state. |
| Exhaustion | Completing the only synthetic target, requesting another batch and reloading/restarting retains needs_data and its message. The completed round and diagnostic stay independently readable. |

## Observed red and correction

On the initial SHA, the literal HTTP sequence create one target → acknowledge its last label → request another round returned `outcome=needs_data`, but GET `/api/training` returned `status=complete` and an empty message. The script failed with `Durable latest needs_data outcome is hidden on hub reload after completed round`. This was reported to the application owner, who independently reproduced it and changed hub outcome projection. The same durable regression now passes across reload and restart while retaining completed history. A5 made no production edits.

## Fingerprints and preservation

The QA script received-byte SHA-256 is `3a101e01f82639821f458597d8123f4da6d1def88e41ecb852e50054f3112c98`.

The 430-file baseline canonical payload SHA-256 is `72f079eacc116b08ed479bfb0bf391ac740c97476b8bc2bb7f92a2b44aa4f1f6`; the baseline file's received-byte SHA-256 is `c0ad60f61c4bd0a60b5e8f15b60b286cf7a6abeeea056075ccb327374bef62fe`. Every mapped received-file digest matched before and after the probe. The frozen detector received-byte SHA remains `76e3e7c08f482a09126593bd375534ff92a1007a971b38ca5fb016966c3ced8a`; review.py remains `aec0b6a02a80da2fd46cbe1a2b58b87382e31f6fd108b9071cfa017042fd3d19`; evaluation.py remains `1f2b9d04aec3af8a39731af2d2d6d9f1c6cb522b3313b9570a1cd3f7290a9757`.

## Claims and limitations

These are synthetic engineering controls, not new market judgments, corpus results, recognition accuracy, independent validation or investment performance. No fake latest user pass was created in the live store. A4's verified outcome remains retain_v1; no candidate was promoted. Process-exit recovery at fsync boundaries does not simulate storage power loss or validate provider/calendar accuracy. The coordinator owns the separate actual-browser acceptance, full `make verify`, final preservation rerun and local delivery; this worker does not claim those future gates complete.

## Next

Coordinator independently reruns `make verify`, this script with `--port 4177`, py_compile and the 430-file preservation guard, then records the approved browser/delivery and final full-SHA remote-equality results. A5 stops after these owned files and evidence are ready.
