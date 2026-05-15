# Telekurs Classification — SIX Financial Information

**Telekurs Classification** is a proprietary industry and sector classification system historically developed by Telekurs and now maintained by **SIX Financial Information**. It is widely used in **Switzerland** across banks, asset managers, custodians, and regulatory reporting workflows.

## Purpose and Scope

The Telekurs classification provides a **Swiss-centric industry taxonomy** for classifying issuers and financial instruments. It is deeply embedded in Swiss market data feeds and operational systems, making it particularly relevant for domestic portfolios and reporting.

## Structure

Telekurs classification follows a **hierarchical sector model**, typically consisting of:

1. **Sector**
2. **Industry Group**
3. **Industry**

The exact depth and naming may vary depending on the data product and historical version, but each issuer or instrument is assigned to a **single primary industry path**.

## What You Get

* Industry and sector classifications tailored to the **Swiss financial market**
* Strong integration with **SIX / Telekurs identifiers** (Valor number, ISIN, MIC)
* Stable classifications aligned with Swiss banking and custody systems

## Regional Context

Telekurs classification is **not a regional model**, but it is **implicitly Swiss-focused**:

* Coverage is strongest for Swiss and European issuers
* Frequently used where **Swiss regulatory, tax, or client reporting** applies
* Regional exposure is still derived via issuer domicile, listings, or revenue data

#### Used For

* Swiss portfolio construction and reporting
* Risk attribution and sector exposure analysis
* Client reporting in Swiss banks and wealth managers
* Regulatory and supervisory disclosures in Switzerland

## Standardization Note

Telekurs classification is a **commercial, proprietary standard**. It is **not ISO-regulated** and is available only via licensed SIX Financial Information data products.

## Modeling Implications

In a financial instrument or issuer ontology, Telekurs classification is typically modeled as:

* A **classification assignment** on the *Issuer* and/or *Instrument*
* A **market-specific classification system** alongside GICS and ICB
* A **time-versioned reference**, as classifications may change over time

Telekurs is often used **in parallel** with global standards (GICS, ICB), not as a replacement, especially in Swiss-domiciled portfolios.

### Telekurs Classification — Normalized ClassificationAssignment Pattern

```yaml
classification_assignment:
  assignment_id: "cls-telekurs-0001"
  classification_system: "Telekurs"
  provider: "SIX Financial Information"

  applies_to:
    entity_type: "Issuer"
    entity_id: "CH0001234567"

  effective_period:
    valid_from: "2024-01-01"
    valid_to: null

  classification_node:
    hierarchy:
      level_1:
        type: "Sector"
        code: "20"
        name: "Financials"

      level_2:
        type: "IndustryGroup"
        code: "2020"
        name: "Banks"

      level_3:
        type: "Industry"
        code: "202010"
        name: "Universal Banks"

  metadata:
    primary_classification: true
    source_feed: "SIX Telekurs Reference Data"
    jurisdiction_focus: "CH"
```

### Ontology Semantics

* **ClassificationAssignment** is a first-class object, not an embedded attribute.
* The assignment:

  * links a **classified entity** (Issuer or Instrument)
  * to a **classification system** (Telekurs)
  * via a **time-bounded validity period**.
* The **classification_node** captures the hierarchical path.
* Higher levels are **contextual**, not independently assigned.

### Why This Pattern Scales

* Supports **multiple parallel classifications** (Telekurs, GICS, ICB)
* Enables **time-travel queries** (historical sector views)
* Cleanly separates:

  * *what* is classified
  * *by which system*
  * *when*
* Works identically for Issuer-level and Instrument-level classifications

### Parallel Example (Conceptual)

```text
Issuer
 ├─ ClassificationAssignment (Telekurs)
 ├─ ClassificationAssignment (GICS)
 └─ ClassificationAssignment (ICB)
```

This allows Swiss-specific reporting (Telekurs) and global comparability (GICS / ICB) without conflating semantics.
