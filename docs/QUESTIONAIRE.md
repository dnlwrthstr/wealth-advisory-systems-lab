# Questionnaire Specification

This document defines the target architecture for configurable advisory questionnaires.

Questionnaires are admin-defined, segment-aware, graph-structured forms that collect client or advisor input and produce evidence for profiling, strategy selection, gating, suitability, and audit trails.

## Goals

- Support flexible question and answer types.
- Allow admins to define, version, review, and publish questionnaires.
- Model questionnaire flow as a graph, not only as a flat list.
- Support conditional subquestions such as ESG exclusions after an ESG preference question.
- Support repeated sections for portfolio-specific answers.
- Preserve the logical navigation order for client and advisor workflows.
- Adapt questionnaire content to client segments.
- Keep questionnaire definitions auditable and machine-readable.
- Render a visual tree/graph beside the questionnaire editor and runtime form.

## Non-Goals

- The questionnaire engine is not the suitability engine.
- The questionnaire graph should not directly place trades, select products, or override gates.
- The first implementation does not need a full visual graph editor with drag-and-drop; a tree preview is enough.

## Core Concepts

```text
Questionnaire
-> Segment
-> Section
-> Question node
-> Answer
-> Edge / transition rule
-> Scoring contribution
-> Ontology mapping
-> Audit evidence
```

## Admin Menu Structure

The frontend should expose admin navigation for questionnaire management:

```text
Admin
├── Questionnaires
│   ├── Drafts
│   ├── Published
│   └── Retired
├── Segments
│   ├── Retail
│   ├── Professional
│   ├── Eligible counterparty
│   └── Custom segments
├── Scoring Rules
├── Ontology Mappings
├── Preview
└── Audit Runs
```

The first useful admin workflow:

1. Create questionnaire.
2. Select applicable client segment.
3. Define sections.
4. Add question nodes.
5. Define answer options and answer type.
6. Define graph transitions.
7. Map questions to ontology paths.
8. Attach scoring rules.
9. Preview questionnaire path.
10. Publish a version.

## Question Types

Questions must support different answer types.

### Boolean

Yes/no or true/false.

Example:

```json
{
  "question_id": "cares_about_esg",
  "type": "boolean",
  "prompt": "Do you care about ESG preferences?"
}
```

### Single Choice

One answer from a fixed list.

Example:

```json
{
  "question_id": "investment_horizon",
  "type": "single_choice",
  "options": [
    { "value": "short_term", "label": "Under 3 years" },
    { "value": "medium_term", "label": "3 to 7 years" },
    { "value": "long_term", "label": "More than 7 years" }
  ]
}
```

### Multiple Choice

Multiple answers from a fixed list.

Example:

```json
{
  "question_id": "excluded_sectors",
  "type": "multiple_choice",
  "options": [
    { "value": "weapons", "label": "Weapons" },
    { "value": "tobacco", "label": "Tobacco" },
    { "value": "thermal_coal", "label": "Thermal coal" }
  ]
}
```

### Gradual / Slider

A numeric scale or shifter.

Example:

```json
{
  "question_id": "loss_comfort",
  "type": "slider",
  "scale": {
    "min": 1,
    "max": 5,
    "step": 1,
    "min_label": "Very uncomfortable",
    "max_label": "Very comfortable"
  }
}
```

### Text

Free text answer for notes, explanations, or restrictions.

Example:

```json
{
  "question_id": "regulatory_restrictions_notes",
  "type": "text",
  "max_length": 1000
}
```

### Image

Image answers are deferred from the first implementation. The architecture should leave room for image choice and image upload later, but the first release should keep question rendering and audit evidence text/data based.

Future image prompt or image-based answer example:

```json
{
  "question_id": "portfolio_style_preference",
  "type": "image_choice",
  "options": [
    {
      "value": "stable_income",
      "label": "Stable income",
      "image_url": "/assets/questionnaires/stable-income.png"
    },
    {
      "value": "growth_path",
      "label": "Growth path",
      "image_url": "/assets/questionnaires/growth-path.png"
    }
  ]
}
```

Future image uploads should be represented as document references, not embedded binary payloads.

```json
{
  "question_id": "evidence_document",
  "type": "image_upload",
  "answer": {
    "document_id": "doc_123",
    "mime_type": "image/png"
  }
}
```

## Flexible Answer Model

Answers should not be restricted to only strings and booleans. The answer model should support:

```text
string
boolean
number
list[string]
list[number]
object
document reference
empty/null for unanswered optional questions
```

Reference answer shape:

```json
{
  "question_id": "excluded_regions",
  "answer": ["US", "CN"],
  "answered_by": "client",
  "answered_at": "2026-05-14T10:30:00Z",
  "evidence_document_ids": []
}
```

## Graph Structure

Questionnaires should be defined as graphs. A graph allows conditional follow-up questions, repeated sections, and advisor-specific branches.

The graph must be acyclic. Users may navigate backward in the UI, but changing an earlier answer recalculates the reachable path instead of creating graph cycles.

Recommended model:

```json
{
  "questionnaire_id": "retail_profile_v1",
  "version": "1.0",
  "entry_node_id": "start",
  "nodes": [
    {
      "node_id": "cares_about_esg",
      "kind": "question",
      "question": {
        "question_id": "cares_about_esg",
        "type": "boolean",
        "prompt": "Do you care about ESG preferences?"
      }
    }
  ],
  "edges": [
    {
      "from": "cares_about_esg",
      "to": "excluded_regions",
      "condition": {
        "question_id": "cares_about_esg",
        "operator": "equals",
        "value": true
      }
    },
    {
      "from": "cares_about_esg",
      "to": "risk_tolerance",
      "condition": {
        "question_id": "cares_about_esg",
        "operator": "equals",
        "value": false
      }
    }
  ]
}
```

## ESG Branch Example

```text
cares_about_esg?
├── yes
│   ├── excluded_regions
│   ├── excluded_sectors
│   ├── minimum_esg_rating
│   └── sustainability_objective
└── no
    └── risk_tolerance
```

This branch should produce constraints and preferences, not direct suitability approval.

## Logical Navigation Order

Even though the questionnaire is a graph, it still needs a clear intended navigation order.

Each node should support:

```json
{
  "display_order": 30,
  "section_id": "constraints_and_preferences",
  "previous_label": "Back",
  "next_label": "Continue"
}
```

The graph controls which node is reachable. The display order controls how admins and reviewers understand the intended sequence.

Recommended high-level order:

1. Client identity and segment.
2. Profiling context.
3. Investment objectives.
4. Financial situation.
5. Risk capacity.
6. Risk tolerance.
7. Knowledge and experience.
8. Constraints and preferences.
9. Advisor review.
10. Confirmation and audit evidence.

## Repeated Sections

Repeated sections are required.

Use cases:

- separate risk tolerance for different portfolios
- ESG preferences per portfolio or mandate
- constraints per account, portfolio, or investment objective

Repeated sections should not be modeled as graph cycles. Instead, the graph node should declare a repeat context.

Example:

```json
{
  "node_id": "portfolio_risk_tolerance",
  "kind": "section",
  "repeat": {
    "enabled": true,
    "context": "portfolio",
    "min_items": 1,
    "max_items": 10
  }
}
```

Answers from repeated sections must include the repeat instance ID.

```json
{
  "question_id": "loss_comfort",
  "repeat_context": "portfolio",
  "repeat_instance_id": "portfolio_core",
  "answer": 3
}
```

## Client Segments

Each questionnaire should declare the segments it applies to.

Examples:

```text
retail
professional
eligible_counterparty
natural_person
legal_entity
advisory
discretionary
execution_only
```

Recommended segment configuration:

```json
{
  "segment_id": "retail_advisory_natural_person",
  "client_type": "retail",
  "legal_form": "natural_person",
  "advisory_type": "advisory",
  "regulation": "FIDLEG"
}
```

Questionnaires should be segment-specific:

```json
{
  "questionnaire_id": "retail_advisory_profile",
  "applies_to_segments": ["retail_advisory_natural_person"]
}
```

Segment adaptation can happen in two ways:

- separate questionnaire per segment
- shared questionnaire with segment-specific nodes and edges

The first implementation should prefer separate questionnaires per segment because it is easier to audit and review.

Questionnaire inheritance should not be used in the first implementation. It looks attractive for reuse, but it tends to make published behavior harder to reason about and review. Shared content can be copied into a new questionnaire version or extracted later into explicit reusable templates if the need becomes clear.

## Ontology Mapping

Each question should optionally map to an ontology path.

Example:

```json
{
  "question_id": "investment_horizon",
  "ontology_path": "client_profile.investment_objectives.investment_horizon"
}
```

This keeps admin-defined questions connected to the controlled domain model in `client_profiling_ontology.yml`.

## Scoring Rules

Scoring rules should be versioned separately from answers.

Simple option-level scoring is acceptable for the first implementation:

```json
{
  "question_id": "loss_20_percent",
  "answer_value": "uncomfortable",
  "target_signal": "risk_tolerance_score",
  "score": 2
}
```

Later, rules can support formulas:

```json
{
  "rule_id": "final_risk_score",
  "calculation": "min(risk_capacity_score, risk_tolerance_score)"
}
```

## JSON-LD / LDJSON Decision

Architectural decision: questionnaire definitions should be stored as JSON-compatible graph documents and should be compatible with JSON-LD.

Reasoning:

- The questionnaire has graph semantics.
- Questions need stable identifiers.
- Nodes should map to ontology paths.
- Audit records need to preserve meaning across versions.
- JSON-LD compatibility lets us add semantic context without forcing a heavy semantic-web stack now.

Recommended storage format:

```text
Postgres JSONB
```

Recommended document style:

```json
{
  "@context": {
    "profile": "https://wealth-advisory-lab.local/ontology/client-profile#"
  },
  "@type": "Questionnaire",
  "questionnaire_id": "retail_profile_v1",
  "version": "1.0",
  "nodes": [],
  "edges": []
}
```

We should not require RDF tooling in the first implementation. JSON-LD compatibility is enough.

## Frontend Requirements

The questionnaire admin frontend should have two coordinated panes:

```text
┌──────────────────────────┬───────────────────────────────┐
│ Tree / Graph Preview     │ Question / Rule Editor         │
│                          │                               │
│ Start                    │ Prompt                        │
│ └─ ESG?                  │ Type                          │
│    ├─ yes                │ Options                       │
│    │  ├─ regions         │ Ontology mapping              │
│    │  └─ sectors         │ Scoring rules                 │
│    └─ no                 │ Navigation conditions         │
│       └─ risk tolerance  │                               │
└──────────────────────────┴───────────────────────────────┘
```

Left pane:

- questionnaire tree
- node status
- conditional branches
- segment visibility markers
- warnings for unreachable nodes

Right pane:

- selected node editor
- question type
- answer options
- validation rules
- ontology mapping
- scoring rules
- transition edges

Runtime frontend should show:

- current section
- current question
- progress through logical order
- advisor/client mode
- warnings for missing or inconsistent answers

Advisors may add review notes. They should not override client answers in the first implementation. If an answer is wrong, the client answer should be amended or superseded with a new answer event so the audit trail remains clear.

## Persistence Model

Suggested tables:

```text
admin.questionnaire_definition
admin.questionnaire_node
admin.questionnaire_edge
admin.scoring_rule
admin.client_segment
audit.questionnaire_answer_run
audit.questionnaire_answer
audit.profile_processing_run
```

For the first implementation, `admin.questionnaire_definition.definition JSONB` can store the full graph. Normalized node/edge tables can be added when editing and querying become more sophisticated.

## Validation Rules

The admin editor should validate:

- duplicate question IDs
- duplicate node IDs
- missing entry node
- missing target nodes for edges
- unreachable nodes
- graph cycles
- missing required ontology mappings
- invalid scoring targets
- segment rules that make a node unreachable

## Versioning

Published questionnaire definitions are immutable.

Allowed lifecycle:

```text
draft -> published -> retired
```

Editing a published questionnaire creates a new draft version.

Every answer run must store:

- questionnaire ID
- questionnaire version
- ontology version
- scoring policy version
- graph definition hash

## Architecture Decisions

### Repeated Sections

Decision: support repeated sections.

Rationale: risk tolerance, ESG preferences, and constraints may differ by portfolio, account, or mandate.

Implementation direction: repeated sections use explicit repeat contexts and repeat instance IDs. They do not use graph cycles.

### Image Answers

Decision: defer image answers from the first implementation.

Rationale: image upload and image choice add document handling, storage, rendering, and audit complexity. The model should allow them later, but the first release should focus on core profiling and gating.

### Advisor Overrides

Decision: advisors can add review notes, but cannot overwrite client answers in the first implementation.

Rationale: client answers are evidence. Advisor input should be additive and auditable.

### Segment Reuse

Decision: do not use questionnaire inheritance in the first implementation.

Rationale: inheritance looks clean at first but becomes difficult to reason about when versions, segments, and audit trails interact.

Implementation direction: use separate questionnaires per segment. Reusable templates can be introduced later if duplication becomes a real maintenance problem.

### Graph Cycles

Decision: questionnaire graphs must be acyclic.

Rationale: cyclic graphs make answer path reconstruction and audit review harder. The UI can allow backward navigation, but the questionnaire definition itself should remain a directed acyclic graph.
