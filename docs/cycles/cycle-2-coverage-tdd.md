# Cycle 2 coverage evidence

The reviewed second-cycle plan authorized two timing regressions at the existing `coverage_report(snapshot, as_of)` seam. Tests use the existing explicitly synthetic complete snapshot. No new data source, permanent headquarters lookback, or strategy rule is introduced.

## Vertical TDD

| Behavior | Exact command run before and after implementation | Observed red | Observed green |
| --- | --- | --- | --- |
| Future latest-period verification cannot clear an earlier decision | `uv run pytest tests/test_coverage.py::test_latest_period_verification_after_decision_is_future -q --tb=short` | 1 failed: `buy_allowed` was incorrectly `True` when verification claimed October 10 at an October 9 decision | 1 passed; latest-period status is `future`, entry blocked, revenue normalization withheld |
| A negative headquarters clearance cannot claim review of future dates | `uv run pytest tests/test_coverage.py::test_headquarters_clearance_reviewing_future_dates_is_future -q --tb=short` | 1 failed: `buy_allowed` was incorrectly `True` when the reviewed lookback ended October 10 at an October 9 decision | 1 passed; headquarters status is `future`, entry blocked |

The regression also checks that source evidence is preserved and the input is unchanged. `fetched_at` remains retrieval provenance; publication time alone controls source availability. This correction evaluates the separate claimed verification date.

## Regression and curated control checks

`uv run pytest tests/test_coverage.py -q` → **140 passed** (138 existing cases plus the two new regressions). `git diff --check` passed. The confirmed headquarters-investment branch remains unchanged and continues excluding independently evidenced positive investment without inventing a lookback policy.

The following checks were manual public-seam replays, not newly failing TDD slices. They replay only the primary-source classification/HQ records from [cycle-2 data research](../research/2026-10-10-cycle-2-data.md); other observations come from the explicitly synthetic demo fixture. These are control checks, not complete real-issuer coverage reports or opportunities.

| Control | Observed eligibility / field status | Buy allowed |
| --- | --- | --- |
| TAVI, issuer publication October 2 | Excluded / classification available | False |
| TAVIU, same dated unit evidence | Excluded / classification available | False |
| TAVIR, unsupported right classification | Unknown / classification available | False |
| FSHP, issuer publication September 15 | Excluded / classification available | False |
| SPY, actual publication time unknown | Unknown / classification unreviewed | False |
| JPM, dated positive headquarters evidence | Excluded / headquarters available | False |
| Synthetic baseline retrieved after its decision cutoff | Prior source publication remains usable; retrieval is provenance | True, for this invented fixture only |

SPY's listing-as-of date was not fabricated into a publication date. The replay supplies no `available_at` when publication is unknown. The curated record capture timestamp is retained as fetch/capture provenance; it does not replace publication.

Exact manual replay command:

```bash
uv run python - <<'PY'
import json
from copy import deepcopy
from pathlib import Path
from gary.coverage import coverage_report

base=json.loads(Path('src/gary/static/demo-snapshot.json').read_text())
curated=json.loads(Path('private/cycle-2/data/curated-controls.json').read_text())
results=[]
for control in curated['controls']:
    if control['symbol'] not in {'TAVI','TAVIU','TAVIR','FSHP','SPY'}:
        continue
    snapshot=deepcopy(base)
    snapshot['symbol']=control['symbol']
    snapshot['classification']={'security_type':control['security_type'],'exchange':'NYSE_ARCA' if control['symbol']=='SPY' else 'NASDAQ','reviewed':True,'source':{'url':control['source_url'],'available_at':control.get('publication_date'),'fetched_at':curated['recorded_at']}}
    report=coverage_report(snapshot,'2026-10-09')
    assert report['buy_allowed'] is False
    expected='unknown' if control['symbol'] in {'SPY','TAVIR'} else 'excluded'
    assert report['eligibility']==expected
    results.append({'symbol':report['symbol'],'eligibility':report['eligibility'],'classification_status':report['fields']['classification']['status'],'buy_allowed':report['buy_allowed'],'publication_evidence':control.get('publication_date','unknown'),'scope':'curated classification only; other observations are synthetic controls'})

jpm=next(control for control in curated['controls'] if control['symbol']=='JPM')
snapshot=deepcopy(base)
snapshot['symbol']='JPM'
snapshot['headquarters']={'state':'confirmed_investment','source':{'url':jpm['source_urls'][-1],'available_at':jpm['press_release_publication_date'],'fetched_at':curated['recorded_at']}}
report=coverage_report(snapshot,'2026-10-09')
assert report['eligibility']=='excluded' and not report['buy_allowed']
results.append({'symbol':'JPM','eligibility':report['eligibility'],'headquarters_status':report['fields']['headquarters']['status'],'buy_allowed':report['buy_allowed'],'scope':'positive-investment branch unchanged; no lookback invented'})

snapshot=deepcopy(base)
def update_fetch(record):
    if isinstance(record,dict):
        if 'source' in record:
            record['source']['fetched_at']=curated['recorded_at']
        for value in record.values():
            update_fetch(value)
update_fetch(snapshot)
report=coverage_report(snapshot,'2026-10-09')
assert report['buy_allowed'] is True
results.append({'symbol':'synthetic cached baseline','buy_allowed':report['buy_allowed'],'scope':'later retrieval time does not replace prior source publication time'})
print(json.dumps(results,indent=2))
PY
```

No new network request was made for these implementation checks. Only `coverage.py`, `test_coverage.py` and this evidence note were edited; no files were staged or committed.
