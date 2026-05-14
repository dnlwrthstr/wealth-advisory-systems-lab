# Repository Split

Investment research and wealth advisory systems overlap, but they should not share one conceptual core.

## Investment Research Lab

Primary question: what is attractive to own, avoid, hedge, or research further?

Recommended focus:

- Valuation
- Financial statements
- Portfolio theory
- Market data
- Factor investing
- Risk analytics
- Technical indicators
- Quant research
- AI research assistants

Typical modules:

- `valuation`
- `risk`
- `portfolio`
- `analytics`
- `ai`

## Wealth Advisory Systems Lab

Primary question: is the advice suitable, compliant, explainable, monitored, and governed for the client?

Recommended focus:

- Advisory workflows
- Client profiling
- Suitability and appropriateness checks
- Compliance monitoring
- Portfolio oversight
- Advisor supervision
- AI governance
- Audit trails and evidence capture

Typical modules:

- `profiling`
- `advice`
- `compliance`
- `monitoring`
- `governance`
- `analytics`

## Why Split Them?

A combined repository tends to blur two different mental models:

- Research systems optimize for analytical insight, signal quality, valuation discipline, and portfolio construction.
- Advisory systems optimize for client context, process integrity, controls, explainability, and regulatory defensibility.

Keeping the labs separate improves pedagogy and architecture. It also makes it easier to reuse investment outputs as inputs to advisory workflows without letting research logic become the advisory control system.

