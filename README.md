# Gary.ai

An investment learning project for investors with deep knowledge of US equity fundamentals. Gary.ai will formalize Gary’s existing stock-selection strategy and determine allocations for a dedicated portfolio of operating-company common stocks listed on US stock exchanges. Positions use whole 100-share blocks.

## Status

The first two research, TDD, local deployment and independent QA cycles are implemented. Cycle 3 adds separate five-year research views and a frozen original-context holdout workflow. The strategy is documented; investment performance remains unvalidated, and recognition reports require independent labels.

## Workflow

Use a grilling interview with domain documentation to challenge assumptions and capture settled definitions and decisions. The upstream [grill-with-docs skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md) combines grilling and domain-modeling.

## Intended sequence

1. Establish the investment mandate and learning workflow.
2. Capture Gary’s existing rules and evaluate their stock-selection and allocation behavior.
3. Eventually expose the resulting workflow through an MCP server for other users.

See [CONTEXT.md](CONTEXT.md) for terminology and [the design interview](docs/design-interview.md) for settled scope and open questions.

## First-version documents

- [Strategy specification](docs/strategy-v1.md)
- [Implementation plan](docs/implementation-plan.md)

Unanswered strategy details are labeled provisional defaults. Brokerage integration, a validated backtest and MCP deployment remain future work.

## Run locally

Install [uv](https://docs.astral.sh/uv/), then run from this checkout:

```bash
uv sync
make verify
make preview
```

Open http://127.0.0.1:4175. The preview is explicitly synthetic and records paper state under ignored `private/`. Run, repeat and reset demonstrate the daily-step interface. It binds only to localhost.

On the original machine with the private eight-symbol pilot cache:

```bash
make review
make preview
```

Open http://127.0.0.1:4175/review for anonymous chart labeling. The frozen study has 180-session views and a 20-session completion band. Choose completed patterns, none, uncertain or unreviewable; saves and explicit revisions preserve history. Holdout charts and predictions are hidden. The server is assigned to Gary by default; reviewer identity cannot be switched through HTTP. This is trusted local research, not a multi-user authentication system.

Queue metadata, cached bars and labels are ignored under `private/cycle-2/`. Rebuilding reproduces the study and refuses to replace a different active queue. A fresh clone lacks these private source files; synthetic paper mode remains runnable. `uv run python -m gary.review_preview report` writes a coordinator-private calibration summary. Only exact agreement between the two registered reviewers enters recognition counts; pending and uncertain labels do not become negatives. No recognition score is shown during labeling.

For the third cycle on the original machine, with its preserved complete calibration copy and three-source private cache:

```bash
make review-cycle3
make preview-cycle3
```

Open http://127.0.0.1:4175/review. Choose five-year exploration, frozen holdout or completed calibration. Five-year cards contain daily history through a fixed cutoff, with a whole-context overview and last-180-session detail; completion labels still apply only to the final 20 sessions. The new sources are separate from the original study. They are research inputs, not screened investment recommendations.

The operator freezes the detector, original contexts, completed calibration labels, holdout predictions, evaluator executable hashes and scoring protocol before either new study is served. The original detector remains v1. Calibration is then read-only; holdout and five-year observations use separate journals under ignored `private/cycle-3/`. Rebuilding cannot replace an active release. Each request verifies the release; five-year cards also reproduce from the retained source cache before display. This is a local research integrity mechanism, not multi-user authentication.

`uv run python -m gary.review_preview report-cycle3` writes private calibration/holdout reports and preserves completed report snapshots. Incomplete holdout passes produce progress with no recognition scores. Complete reports require two exact certain reviewers, keep random/enriched and time/source-held-out strata separate, and identify the frozen version and label snapshot. Holdout feedback cannot tune that evaluated version; later recognition changes need fresh validation. Five-year charts do not constitute a five-year investment backtest.

With the retained historical cache, `uv run python -m gary.review_preview holdout-context` adds five-year overviews to the original 13 holdout cards. Open `/review?study=holdout` after restarting the preview. Each overview ends at that card's historical cutoff; its final 180 bars must match the original exactly. The unchanged detail and final-20-session labeling band remain below it. Each view uses its own price index and median volume, with anonymous markers for reported splits. Provider adjustment accuracy and exchange-calendar completeness remain unverified.

These additional observations use a separate `five-year-assisted-v1` queue and journal under ignored `private/cycle-3/holdout-context/`; original observations are never imported. The original view remains read-only at `/review?study=holdout-original`. Saves require the displayed view's opaque token, so older tabs must reload. Expanded history can overlap previously exposed calibration history; its separate report cannot be interpreted as the original same-view holdout score. `uv run python scripts/check_holdout_context.py` checks retained-source reconstruction and preservation on the original machine. Source data remain private and a fresh clone cannot build these real charts without its own retained cache.

`make coverage` summarizes this machine's ignored cached pilot evidence. A fresh clone has no raw provider cache and reports that absence; see `uv run python -m gary.coverage_probe --help` for an optional bounded live probe. Full vendor datasets are not committed.

## Agent development cycle

Research Dot → reviewed contracts → one failing behavior test → minimum passing implementation → local preview → independent QA → failing regression → correction and recheck.

- [Research findings](docs/research/2026-10-10-first-cycle.md)
- [Approved agent plan](docs/plans/2026-10-10-agent-cycle.md)
- [Reusable role briefs](docs/prompts/2026-10-10-agent-cycle.md)
- [First-cycle results](docs/cycles/2026-10-10-first-cycle.md)
- [Second-cycle plan](docs/plans/2026-10-10-cycle-2.md)
- [Second-cycle contracts](docs/cycle-2-contracts.md)
- [Second-cycle data audit](docs/research/2026-10-10-cycle-2-data.md)
- [Second-cycle sampling protocol](docs/research/2026-10-10-cycle-2-patterns.md)
- [Second-cycle results and QA](docs/cycles/2026-10-10-cycle-2.md)
- [Third-cycle approved plan](docs/plans/2026-10-10-cycle-3.md)
- [Third-cycle confirmed interfaces](docs/cycle-3-contracts.md)
- [Third-cycle results and QA](docs/cycles/2026-10-10-cycle-3.md)
- [Historical holdout context plan](docs/plans/2026-10-11-holdout-context.md)
- [Historical holdout context delivery and QA](docs/cycles/2026-10-11-holdout-context.md)

The strategy core has three pure interfaces: coverage reports, causal pattern recognition and paper daily execution. The review workflow adds queue construction, versioned labels and calibration summaries. Tests use synthetic evidence and check observable behavior. The live pilot supports source-access and workflow feasibility; it is not an automatic source of reviewed candidates. Independent human labels, compliant SEC access and reviewed headquarters evidence remain required before recognition and real-data portfolio claims.
