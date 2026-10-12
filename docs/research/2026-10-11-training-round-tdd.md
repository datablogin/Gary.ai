# Training-round TDD evidence

A2 worker complete on October 12, 2026. The coordinator independently verifies this assignment before releasing A3. This document contains synthetic engineering controls only; no real judgments, company-case mapping or comparison scores were inspected or published.

Ownership: new `src/gary/training.py`, `tests/test_training.py`, and this document. The four approved seams are `build_review_queue(series, config)`, `record_review_label(queue, labels, entry)`, `summarize_review(queue, labels)`, and `request_training_round(catalog, history, request)`. Tests use these public seams without internal mocks. The approved TDD skill, tests/mocking guidance, plan, dispatch, role brief, scorecard, CONTEXT and frozen A0/A1 contracts were read before implementation. No applicable ancestor or repository AGENTS.md/CLAUDE.md was found at launch.

## Observed vertical slices

Each implementation slice began with its behavior test, an observed failure, the minimum supporting change, and a green rerun. The commands used `.venv/bin/python -m pytest tests/test_training.py -q -k <test-name-fragment>`, followed by the growing saved suite.

| Behavior | Observed red | Minimum green |
| --- | --- | --- |
| Anonymous five-year queue and exact180 reference | Missing training module at collection. | Deterministic queue, cards, memberships and A1 reference recipe. First test passed. |
| Missing legacy exposure | Four fixtures allocated despite missing/incomplete evidence. | Explicit no-candidate exclusions; never default to an empty ledger. |
| Reviewed source admission | Seven missing/malformed provenance fixtures allocated. | Reviewed operating-common classification, canonical aliases, lineage receipts and source metadata. |
| Frozen config | Seven changed profile/manifest/type/policy fixtures were accepted. | Strict fields, integer seeds excluding bool, assigned human and pinned v1 manifest. |
| Five-year boundaries |1199 sessions and start gap8 were admitted. | Require1200 and open-left anniversary+1..7, exact endpoint and raw180 tail. Literal1200/+7 and Feb29 controls were already green. |
| Full source and cutoff integrity | Seven malformed OHLCV/split/cutoff fixtures failed their expected exclusion behavior. | Validate all retained bars, explicit unique cutoff frame and reject reported full-view splits. |
| Exposure boundaries | Prior target/exact-window and reservation fixtures allocated. | Canonical alias resolution, inclusive target overlap, exact-window checks, and active source-or-full-context reservation rejection. |
| Broader history exposure | Allowed overlap lacked its required record. | Preserve prior view rows and development-only interpretation in each case. |
| Actual sampling frames | The public queue lacked frame records. | Record the deduplicated explicit random/enriched frames and sizes; bounded6+6 memberships. |
| Canonical duplicate/target sampling | Alias copies entered a frame twice; two overlapping target20 cases entered one batch. | One canonical window per frame and distinct target intervals within the selected batch. |
| Sole human save | Missing public label function. | Normalize observations and derive immutable view/reference/version/input stamps; identical retry preserves history. |
| Token first | Missing/stale tokens reached corrupt-history validation and raised TypeError. | Reject exact-token mismatch first, before other validation. |
| Explicit revisions | A changed label appended without revise/current-revision controls. | Require explicit current revision, preserve superseded row, retry remains stable. |
| Pending summary | Missing public summary function. | Ready/labeling progress and own labels, with null diagnostics/pass and no snapshots. |
| Completion/revisions | Complete history still returned labeling. | A1 personal diagnostic plus separate first/superseding completed-history snapshots. |
| Acknowledged history | Eight corrupt partial histories were accepted. | Rebuild normalized observations and all generated stamps using canonical typed JSON equality. |
| Coherent queue changes | Eight rehashed input/prediction/protocol/card/frame/identity changes were accepted. | Rebuild queue against retained full source inputs and frozen config before labels/summary. |
| Round creation/resume | Missing public request function. | One committed allocation; same-key stable receipt; new request resumes ready or labeling. |
| Request conflict | Same ID with a changed config was accepted. | Reject changed payload hash before transition. |
| Missing data | Four fixtures created empty/unsupported rounds or raised a raw TypeError. | Stable needs_data receipt with no round/exposure allocation. |
| Catalog/history binding | Catalog-only exposure changes allocated. | Require canonical catalog and history exposure equality on allocation. |
| Durable replay | Eight allocation/history mutations were accepted. | Rebuild queue, source/catalog/exposure receipts, status, snapshots, creating request, and all exposure allocations; reject multiple active rounds. |
| Exchange-local completion | Same-day pre-close and UTC/local-day mismatch cutoffs were admitted. | Convert retained fetched_at into source exchange timezone; same-day cutoff requires16:00 or later. |
| Malformed containers | Seven malformed series fixtures crashed or omitted exclusions. | Explicit malformed-container/row admission exclusions and valid empty summary. A temporary indentation typo during this minimum edit was corrected before green. |
| Source fingerprints | Public sealed source receipts were absent. | Commit received-file digest separately from canonical full-source/bars/classification/lineage hashes. |
| Duplicate source IDs | A conflicting duplicate source ID still allocated. | Exclude both duplicate source records. |
| Caller-derived stamps | An injected reference stamp was silently accepted. | Exact entry fields; all generated stamps remain server-owned. |
| Incomplete/malformed catalog | Missing sources raised KeyError; malformed catalog variants returned needs_data. | Missing source/exposure data yields needs_data; unsupported schema/container fails with ValueError. |
| Malformed source time | fetched_at=None raised AttributeError. | Treat malformed time metadata as source-admission exclusion. |
| Request receipt integrity | Injected request exclusions were accepted. | Require receipt exclusions to equal its linked committed round. |

Additional green regression controls verify deterministic input reordering, caps/memberships, historical post-cutoff bar exclusion, unchanged caller inputs, post-completion revision snapshot retention, and complete create → ready resume → labeling resume → completion → another round. A1's52 saved analysis tests supply literal inclusive+3/rejected+4/never-early matching, uncertain/invalid exclusion, overlapping-stratum and null-denominator controls through the already-approved analysis seam.

## Concrete adapter recipe

`tests/test_training.py` exposes synthetic fixture helpers, not new product seams: `synthetic_source`, `exposure`, `config`, `empty_labels`, `entry`, `round_fixture`, and `acknowledge_label`. `round_fixture(8)` supplies a catalog with eight independently named synthetic issuers, a complete evidence-backed empty development ledger, an empty history and a stable base request config without exposure. The first flat-series round has six random cases; the next round has the remaining two.

Exposure evidence is a nonempty list of `{path, received_sha256}`. Aliases map source/symbol aliases to reviewed canonical issuer IDs. Targets carry `{canonical_id,start,end,case_fingerprint,provenance}`; views omit case_fingerprint; reservations additionally carry strict boolean `active`. Provenance is a nonempty string. Strict `complete is True` and `reviewed is True` checks reject numeric substitutes. Unknown legacy lineage/interval evidence blocks admission. Canonical case_fingerprint is the hash of `{canonical_id,as_of,window_hash}`; compatibility checks also exclude previously recorded exact raw180/fullcontext hashes.

The queue seals full admitted source objects and per-source `{source_sha256,source_payload_hash,input_bars_hash,classification_hash,alias_evidence_hash}` receipts. Cases reference those receipts, exact `raw_window`180, `raw_context`5y, final20 dates, memberships and prior-view overlap. `sealed.reference` uses A1's fixed matching protocol, trusted manifest, `prediction_hash=hash({case_id:predictions})`, `inputs_hash=hash({case_id:hash(raw_window)})`, `context_sessions=180`, and `visual_context_years=5`. Its commitment hash excludes itself; queue_hash hashes the full queue excluding itself and is the exact view token.

Transition output is `{status,round_id,round,history,exclusions}`. A round has `{round_id,status,queue,labels,snapshots,allocation}`; allocation contains the original catalog plus canonical catalog/sources/exposure hashes, making rejected-source and accepted-source allocations reproducible. Request records contain `{payload_hash,round_id,outcome,request,exclusions}`. The full original request permits receipt reconstruction. An identical request returns its recorded outcome and current linked round without changing history, including after another round is active. A new request resumes the active ready/labeling round. An identical needs_data request remains needs_data; a later attempt after data repair uses a new request ID.

All displayed target20 intervals and full views are conservatively allocated immediately, before labels, with provenance `training-round:{round_id}:{queue_hash}`. No fictional received-byte evidence receipt is appended. Replay starts from the first queue's sealed base exposure, reproduces each allocation and requires exact equality with current history exposure. Catalog exposure must equal that history on new allocation. The adapter must persist request, queue and allocation in one durable transaction.

After save, the adapter replaces that round's labels with `record_review_label(...)`, obtains `summarize_review(...)`, and stores the returned status and snapshots in the same transaction. Each summary snapshot is `{pass_hash,completed_pass,diagnostic,supersedes_pass_hash}`. Snapshots enumerate every complete acknowledged-history prefix; the first uses supersedes=null, later revisions reference the immediately preceding pass hash. Sidecars should append only unseen pass hashes, preserving every prior snapshot/report. Pending summaries expose progress/own labels and no diagnostic or snapshot.

## Literal verification

```sh
/Users/robertwelborn/.local/bin/uv run pytest tests/test_training.py tests/test_training_analysis.py -q
git diff --check
```

Initial observed gate:158 passed in19.15s. After the independently discovered alias-map correction below, the same command passed159 tests in21.71s. The A0 literal schema/five-seam/thirteen-case checks and all430 received-byte preservation hashes passed again. No installation, fetching, git mutation, UI/adapter edit or old artifact write occurred.

Public fixture replay, using the existing environment:

```sh
PYTHONPATH=tests .venv/bin/python - <<'PY'
from copy import deepcopy
from test_training import round_fixture, acknowledge_label, entry, digest
from gary.training import request_training_round
catalog, history, request = round_fixture(8)
first = request_training_round(catalog, history, request)
queue, round_id = first['round']['queue'], first['round_id']
resumed = request_training_round(catalog, first['history'], request | {'request_id':'synthetic-click-ready'})
assert resumed['status']=='resumed' and resumed['round_id']==round_id
history = acknowledge_label(resumed['history'], round_id, entry(queue))
resumed = request_training_round(catalog, history, request | {'request_id':'synthetic-click-labeling'})
assert resumed['round']['status']=='labeling'
history = resumed['history']
for key in queue['order'][1:]:
    history = acknowledge_label(history, round_id, entry(queue, case_id=key))
original = deepcopy(history['rounds'][0])
assert original['status']=='complete' and len(original['snapshots'])==1
next_catalog = catalog | {'exposure':deepcopy(history['exposure'])}
second = request_training_round(next_catalog, history, request | {'request_id':'synthetic-click-next'})
assert second['status']=='created' and len(second['round']['queue']['order'])==2
assert second['history']['rounds'][0]==original
assert sum(row['status'] in {'ready','labeling'} for row in second['history']['rounds'])==1
assert request_training_round(next_catalog, second['history'], request)['round']==original
print('synthetic public-seam replay verified')
print('first_queue_hash',queue['queue_hash'])
print('first_pass_hash',original['snapshots'][0]['pass_hash'])
print('two_round_history_hash',digest(second['history']))
PY
```

Observed synthetic fingerprints: first queue `cc26a34f2949668415bd098457c0e25f2effa3f62ce1cc5787a8217d203e5e82`; first pass `88a4149aa47fbe469928d93d41398deef0e0aba82e53e1e92af8f30b53871512`; final two-round history `029e4fd0d7e6b262ee6497aa832920d69345342d0db73d99e5f5991d133dbdad`.

The pure core has no own filesystem/network operations. Complete diagnostics use the A1 analysis seam, whose existing trusted-detector helper independently reads frozen executable bytes. Embedded source/evidence hashes do not authenticate external origin: A3 must verify actual retained received bytes, reparsed bars, reviewed classification/alias evidence, legacy bootstrap, durable events and the executable registry before serving or mutating rounds. Full-view bars are historical context, never expanded detector inputs. Reports remain personal development diagnostics; no independent accuracy, financial clearance, future human review or investment-performance result is claimed. A2 stops before A3 or delivery.

## Independent alias-map correction

The coordinator independently passed the initial158-test, public-sequence and430-file gates, then reproduced an adversarial canonical-target bypass through the public builder. Source aliases mapped to `canonical-alias`, while that map key itself mapped to the true issuer holding the prior target. The source's raw canonical field and interval resolution disagreed.

One new behavior regression, `test_nonterminal_alias_map_cannot_bypass_a_previously_exposed_canonical_target`, reproduced the exact bypass: the targeted command failed because a case was admitted. The minimum fix requires every alias-map value to be terminal; a value may also be a key only when it maps to itself. Nonterminal chains, conflicting values and cycles fail complete-ledger admission conservatively. The targeted command then passed:

```sh
.venv/bin/python -m pytest tests/test_training.py -q -k nonterminal_alias_map
```

A separate public builder/request probe admitted a valid canonical self-map and returned a stable needs_data transition for the chained alias fixture, preserving exposure without allocation. The combined suite passed159 tests; the literal A0 contracts and all430 original byte hashes, py_compile, and git diff --check passed again. No adapter or public-contract changes were needed.
