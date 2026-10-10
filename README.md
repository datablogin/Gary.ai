# Gary.ai

An investment learning project for investors with deep knowledge of US equity fundamentals. Gary.ai will formalize Gary’s existing stock-selection strategy and determine allocations for a dedicated portfolio of operating-company common stocks listed on US stock exchanges. Positions use whole 100-share blocks.

## Status

Design interview in progress. Gary’s existing strategy is the starting point; its rules and allocation model have not yet been captured or validated.

## Workflow

Use a grilling interview with domain documentation to challenge assumptions and capture settled definitions and decisions. The upstream [grill-with-docs skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md) combines grilling and domain-modeling.

## Intended sequence

1. Establish the investment mandate and learning workflow.
2. Capture Gary’s existing rules and evaluate their stock-selection and allocation behavior.
3. Eventually expose the resulting workflow through an MCP server for other users.

See [CONTEXT.md](CONTEXT.md) for terminology and [the design interview](docs/design-interview.md) for settled scope and open questions.
