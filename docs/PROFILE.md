# Client Profiling Questionnaire Specification

This document defines the reference flow for turning questionnaire answers into a client profile that can be used by advisory suitability checks.

The notebook layer should teach the concepts and call the functions in `src/profiling`. The source modules are the reference implementation.

## Design Goals

- Keep raw answers separate from derived client profile fields.
- Make scoring assumptions explicit and testable.
- Preserve enough evidence to reconstruct why a profile was derived.
- Treat missing and contradictory answers as first-class validation outcomes.
- Derive advisory profile fields before suitability logic runs.

## Processing Flow

```text
questionnaire definition
-> raw answer set
-> validated answer set
-> scored profile signals
-> derived ClientProfile
-> strategy profile and gate decisions
-> suitability checks
```

Suitability checks must not read raw questionnaire answers directly. They should consume `ClientProfile` and product attributes.

## Admin Configuration Model

Admin functionality owns the questionnaire definition and scoring rules. A questionnaire definition contains:

- stable questionnaire ID
- version
- ordered question definitions
- allowed answer options
- per-option scoring contribution
- target signal for each question
- ontology path for each question
- required/optional marker

The first reference implementation keeps the scoring contribution on each answer option. That keeps admin-defined rules easy to inspect:

```text
question -> ontology path -> answer option -> target signal -> score contribution
```

Later policy versions can move these rules into separate versioned scoring policy objects without changing the processing flow.

## Reference Source Layout

```text
src/profiling/
├── models.py          # ClientProfile, RiskLevel, KnowledgeLevel
├── questionnaire.py   # Question, Questionnaire, AnswerSet, example_questionnaire
├── scoring.py         # score_answers and ProfileScores
├── derivation.py      # derive_client_profile and ProfileDerivation
├── strategy.py        # derive strategy profile and gate decisions
└── signals.py         # derived advisory signals from ClientProfile
```

## Questionnaire Scope

The first reference questionnaire focuses on:

- Risk tolerance: willingness to accept volatility and losses.
- Investment knowledge: experience and product familiarity.
- Investment horizon: expected holding period.
- Liquidity needs: expected near-term withdrawals.
- Dependents: obligation pressure affecting risk capacity.

## Required Question IDs

The reference questionnaire uses these stable IDs:

- `loss_reaction`
- `portfolio_decline_comfort`
- `investment_experience`
- `product_knowledge`
- `horizon`
- `liquidity_need`
- `has_dependents`

Question IDs are part of the audit trail. They should not be renamed casually once used in examples, tests, or persisted records.

## Scoring Signals

Answers are converted into intermediate scores:

- `risk_willingness_score`: client willingness to accept losses.
- `knowledge_score`: client understanding of investment products.
- `horizon_score`: investment time horizon.
- `liquidity_pressure_score`: near-term liquidity pressure.
- `obligation_score`: pressure from dependents or similar obligations.

Scores are intentionally simple integer scales so the notebooks can explain them without hiding assumptions.

## Derived Profile Mapping

The reference derivation maps scores into:

- `risk_tolerance`: `low`, `medium`, or `high`.
- `investment_knowledge`: `basic`, `intermediate`, or `advanced`.
- `instrument_knowledge`: instrument-level experience for equities, bonds, funds/ETFs, derivatives, and structured products.
- `investment_horizon_years`: representative numeric horizon.
- `liquidity_need_12m`: representative near-term liquidity need.
- `has_dependents`: boolean obligation marker.
- `strategy`: capital preservation, balanced growth, or capital growth.
- `risk_profile.category`: defensive, conservative, balanced, or growth.
- `suitability_envelope`: allowed asset classes, exclusions, leverage, and exposure bounds.
- `gates`: suitability pre-checks and human-review requirements.

Default financial fields are supplied by the caller or by conservative example defaults in the teaching flow:

- `age`
- `annual_income`
- `liquid_net_worth`

## Validation Rules

The processor must report:

- missing required answers
- unknown question IDs
- invalid answer choices
- contradictory answers

Contradictions do not always block derivation, but they must be visible as warnings. A conservative derivation may still produce a profile while preserving the warning evidence.

The initial contradiction rule is:

- If `loss_reaction` indicates aggressive buying after a loss but `portfolio_decline_comfort` indicates low loss comfort, flag the answers as contradictory.

## Audit Evidence

The scored output should retain:

- `client_id`
- `questionnaire_id`
- `questionnaire_version`
- per-answer score contributions with ontology paths
- validation warnings

This keeps the implementation suitable for later storage in an advisory audit table.

## Strategy and Gating

The strategy profile is derived after `ClientProfile`, because risk capacity combines questionnaire-derived data with financial context.

Initial reference mapping:

- combined risk profile `low` -> strategy `capital_preservation`
- combined risk profile `medium` -> strategy `balanced_growth`
- combined risk profile `high` -> strategy `capital_growth`

The risk profile category follows the ontology:

- low risk with very short horizon or high liquidity pressure -> `defensive`
- other low risk -> `conservative`
- medium risk -> `balanced`
- high risk -> `growth`

Initial gate decisions:

- Block products whose risk level exceeds the combined client risk profile.
- Block products whose instrument type requires more experience than the client has for that instrument.
- Require daily liquidity when near-term liquidity pressure is material.
- Require human review when questionnaire warnings exist.

Gates are not a replacement for suitability. They are the structured pre-checks and review markers that feed the suitability layer.

## Admin API Shape

The backend exposes reference admin endpoints:

- `GET /admin/questionnaires`
- `POST /admin/questionnaires`
- `GET /admin/questionnaires/{questionnaire_id}`
- `POST /admin/questionnaires/{questionnaire_id}/process`

The process endpoint accepts raw answers and financial context, then returns:

- validation/scoring evidence
- derived `ClientProfile`
- strategy profile
- gate decisions
- persisted `processing_run_id` when audit persistence is enabled

The current backend questionnaire registry is intentionally in-memory. Profile processing audit records are persisted to Postgres when `DATABASE_URL` is configured.

## Audit Persistence

Profile processing creates an audit record containing:

- raw answers
- ontology version
- questionnaire ID and version
- score contributions with ontology paths
- derived profile
- strategy profile
- gate decisions
- warnings and validation errors

The backend writes these records to `audit.profile_processing_run` when audit persistence is enabled.
