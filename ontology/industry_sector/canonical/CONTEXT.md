# Classification Model — Canonical Structure

This structure defines how any industry, sector, or thematic classification is represented and assigned in a financial data model.

## ClassificationSystem

Defines the classification standard itself.

```yaml
classification_system:
  system_id: "telekurs"
  name: "Telekurs Classification"
  provider: "SIX Financial Information"
  type: "IndustryClassification"
  jurisdiction_scope: "CH"
  proprietary: true
  version: "2024"
```

## ClassificationNode

Defines a node within a classification hierarchy.

```yaml
classification_node:
  node_id: "telekurs-202010"
  system_id: "telekurs"
  level: 3
  level_name: "Industry"
  code: "202010"
  name: "Universal Banks"
  parent_node_id: "telekurs-2020"
```

Notes:

* Nodes form a **directed hierarchy**
* Only **one parent per node**
* Level numbering is system-specific


## ClassificationHierarchy (optional explicit definition)

Defines the allowed hierarchy levels for a system.

```yaml
classification_hierarchy:
  system_id: "telekurs"
  levels:
    - level: 1
      name: "Sector"
    - level: 2
      name: "IndustryGroup"
    - level: 3
      name: "Industry"
```

## ClassificationAssignment

Links a classified entity to a classification node.

```yaml
classification_assignment:
  assignment_id: "cls-000001"
  system_id: "telekurs"

  applies_to:
    entity_type: "Issuer"      # Issuer | Instrument | Portfolio
    entity_id: "CH0001234567"

  classification_node_id: "telekurs-202010"

  effective_period:
    valid_from: "2024-01-01"
    valid_to: null

  attributes:
    primary: true
    confidence: "high"
    source: "SIX Reference Data"
```

## Design Rules (Normative)

* An entity **may have multiple ClassificationAssignments**
* Each assignment:

  * belongs to **one ClassificationSystem**
  * points to **one terminal ClassificationNode**
* Higher-level classifications are **derived**, not assigned
* Assignments are **time-versioned**
* Regional information is **never embedded** in classifications

## Example Usage

```text
Issuer
 ├─ ClassificationAssignment (Telekurs)
 ├─ ClassificationAssignment (GICS)
 └─ ClassificationAssignment (ICB)
```

This enables:

* Swiss-specific reporting (Telekurs)
* Global comparability (GICS, ICB)
* Clean separation of concerns

## Why This Structure Works

* Scales across **multiple vendors and standards**
* Supports **reclassification over time**
* Maps cleanly to:

  * YAML schemas
  * Relational models
  * Graph / RDF ontologies
* Avoids hard-coding classification logic into Issuer or Instrument models

## Classification Ontology — Alignment with Issuer & FinancialInstrument

This section defines how the **ClassificationAssignment ontology** integrates *exactly* with the existing **Issuer** and **FinancialInstrument** schemas.

### 1. Issuer (Aligned Schema Fragment)

The Issuer does **not** contain classification attributes.
It exposes only **references** to ClassificationAssignments.

```yaml
issuer:
  issuer_id: "CH0001234567"
  name: "Example Bank AG"
  lei: "5493001KJTIIGC8Y1R12"
  domicile_country: "CH"

  classification_assignments:
    - "cls-telekurs-0001"
    - "cls-gics-0009"
    - "cls-icb-0023"
```

**Normative rule**

* Issuer owns **zero or more** classification references
* Issuer has **no knowledge** of hierarchy or system semantics


### FinancialInstrument (Aligned Schema Fragment)

Instruments may **inherit** issuer classifications or define their own.

```yaml
financial_instrument:
  instrument_id: "CH0012345678"
  instrument_type: "Equity"
  issuer_id: "CH0001234567"

  classification_assignments:
    - "cls-telekurs-0001"   # inherited issuer classification
```

**Normative rule**

* Instrument-level classification is optional
* If absent, issuer-level classification applies by default
* Overrides must be explicit

---

### ClassificationAssignment (Authoritative Object)

ClassificationAssignment is the **only** object linking domain entities to classifications.

```yaml
classification_assignment:
  assignment_id: "cls-telekurs-0001"
  system_id: "telekurs"

  applies_to:
    entity_type: "Issuer"        # Issuer | FinancialInstrument
    entity_id: "CH0001234567"

  classification_node_id: "telekurs-202010"

  effective_period:
    valid_from: "2024-01-01"
    valid_to: null

  attributes:
    primary: true
    confidence: "high"
    source: "SIX Reference Data"
```

### ClassificationNode (Shared Across Issuer & Instrument)

```yaml
classification_node:
  node_id: "telekurs-202010"
  system_id: "telekurs"
  level: 3
  level_name: "Industry"
  code: "202010"
  name: "Universal Banks"
  parent_node_id: "telekurs-2020"
```

**Normative rule**

* Only **terminal nodes** may be assigned
* Higher levels are resolved via traversal


### Relationship Model (Canonical)

```text
Issuer
 ├─ ClassificationAssignment ──┐
 │                              └─ ClassificationNode
 │
FinancialInstrument
 └─ ClassificationAssignment ───┘
```

### Alignment Guarantees

This alignment ensures:

* ✅ **No classification leakage** into Issuer / Instrument
* ✅ **Parallel systems** (Telekurs, GICS, ICB) coexist cleanly
* ✅ **Time-versioned reclassification** is first-class
* ✅ **Ontology / graph mapping** is trivial
* ✅ **Regulatory reporting** can query historical state

---

### Explicit Non-Goals

* Classification systems do **not** store regional data
* Issuer / Instrument do **not** embed sector fields
* No implicit inheritance without reference
* No system-specific logic in core domain entities


### Final Consistency Check

| Concept                  | Defined Once | Referenced By      |
| ------------------------ | ------------ | ------------------ |
| Issuer                   | ✔            | Instrument         |
| FinancialInstrument      | ✔            | —                  |
| ClassificationSystem     | ✔            | Assignment         |
| ClassificationNode       | ✔            | Assignment         |
| ClassificationAssignment | ✔            | Issuer, Instrument |


This is now **fully aligned 1:1** with a clean FinancialInstrument / Issuer ontology.

If you want next, I can:

* collapse this into **validated JSON Schema**
* generate **Neo4j / RDF triples**
* enforce this with **Pydantic models**
* show **query patterns** (OpenSearch / SQL / Cypher)
