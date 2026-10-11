# Gary.ai

An investment learning project for investors with deep knowledge of US equity fundamentals. Gary.ai will formalize Gary’s existing stock-selection strategy and determine allocations for a dedicated portfolio of operating-company common stocks listed on US stock exchanges. Positions use whole 100-share blocks.

## Status

The first research, TDD, local deployment and independent QA cycle is implemented. The strategy is documented; data and chart recognition remain experimental. No investment performance has been validated.

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

`make coverage` summarizes this machine's ignored cached pilot evidence. A fresh clone has no raw provider cache and reports that absence; see `uv run python -m gary.coverage_probe --help` for an optional bounded live probe. Full vendor datasets are not committed.

## Agent development cycle

Research Dot → reviewed contracts → one failing behavior test → minimum passing implementation → local preview → independent QA → failing regression → correction and recheck.

- [Research findings](docs/research/2026-10-10-first-cycle.md)
- [Approved agent plan](docs/plans/2026-10-10-agent-cycle.md)
- [Reusable role briefs](docs/prompts/2026-10-10-agent-cycle.md)
- [First-cycle results](docs/cycles/2026-10-10-first-cycle.md)

The core has three pure interfaces: coverage reports, causal pattern recognition and paper daily execution. Tests use synthetic evidence and check observable behavior. The live pilot supports data-access feasibility only; it is not an automatic source of reviewed candidates. Subsequent cycles should collect independent real-chart labels and resolve classification, financial freshness and headquarters evidence gaps before enabling a real-data portfolio.
