# Review navigation at the final chart

Symptom: Next was disabled while the review still had missing judgments. Diagnosis used the actual browser DOM: the chart heading was at the final card, while the progress number counted completed judgments. No loading/error condition was present. The two counts describe different things. The existing final-index boundary disabled navigation even when earlier charts were still unreviewed.

A read-only DOM feedback check reproduced the precise dead end before editing: `reviewed < total && next.disabled`, with the final-chart heading and loading=false. Direct UI state and the boundary expression established the cause, so speculative hypotheses/instrumentation were unnecessary. No correctness regression belongs to the already confirmed investment/review Python seams; this small frontend change is verified at the actual DOM without adding implementation-mirroring unit tests.

The Next control now preserves chronological navigation and offers Next unreviewed from the last chart when earlier gaps exist. It excludes the current card and stays disabled at the end of a complete or read-only pass. A bounded one-based chart query supports opening the exact affected card for reproduction; out-of-range values fall back to the first card. Study changes still start at the first card.

Verification: JavaScript syntax check and clean diff; actual browser final-chart navigation, first unreviewed destination and preserved read-only end boundary. Label artifacts are compared by SHA-256 before/after; no judgment is saved or revised during this work. No temporary debug logging was added.
