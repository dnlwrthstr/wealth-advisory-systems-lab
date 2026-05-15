# ESG Rating

## Definition

ESG ratings assess how well an issuer or, in some cases, a specific financial instrument, manages Environmental (E), Social (S), and Governance (G) risks and opportunities that may be financially material. The objective is to inform investment decision-making, risk management, and regulatory or client disclosures rather than to certify ethical behavior.
[ESG Rating](https://w3id.org/okn/o/sdm#ESGRating)

## What exactly is being rated?

### Issuer-level (dominant in practice)

Most ESG ratings are issuer-centric:

- The score reflects the sustainability risk profile of the company or sovereign.
- Instruments (equities, bonds) typically inherit the issuer’s ESG characteristics.

Common use:

- Equity selection and portfolio tilts
- Credit risk overlays for corporate bonds
- Engagement and stewardship prioritization

###Instrument-level (supplementary)

Some instruments carry additional ESG attributes beyond the issuer:

- Green / Social / Sustainability bonds: use-of-proceeds, project eligibility, reporting commitments
- Funds / ETFs: portfolio aggregation rules, exclusions, and weighting methodologies

In these cases, the instrument has its own ESG metadata, often layered on top of issuer scores.

## The three pillars

- Environmental (E): Climate exposure, emissions, resource use, pollution, biodiversity.
- Social (S): Labor practices, health & safety, supply chains, customer responsibility, community impact.
- Governance (G): Board structure, shareholder rights, executive pay, audit quality, corruption controls.

Each pillar is scored and then weighted into a composite score according to the provider’s materiality model.

##  Who produces ESG ratings?

Multiple commercial providers exist, each with distinct methodologies and coverage:

- MSCI ESG Ratings
- Sustainalytics
- S&P Global ESG Scores
- Moody’s ESG Solutions
- ISS ESG

There is **no** ISO standard and no single “correct” score. Divergence across providers is normal due to differences in:

- Issue selection and materiality weights
- Data sources (reported vs. estimated)
- Normalization and peer grouping
- Treatment of controversies

## How ESG ratings are used for instruments

| Use case                   | How the rating is applied                   |
| -------------------------- | ------------------------------------------- |
| **Portfolio construction** | Screening, tilting, best-in-class selection |
| **Risk management**        | Identify long-term non-financial risks      |
| **Product labeling**       | ESG / Article 8–9 style classifications     |
| **Reporting**              | Client factsheets, regulatory disclosures   |
| **Index construction**     | ESG-weighted or exclusionary indices        |

## Key limitations (important)

- Comparability: Scores are provider-specific; cross-provider comparisons are weak.
- Backward-looking bias: Heavily reliant on historical disclosures.
- Coverage gaps: SMEs, private issuers, and EMs may be thinly covered.
- Signal vs. values: ESG ratings measure financially material risk, not moral virtue.

## Practical modeling guidance (ontology perspective)

- Treat ESG as reference data, not intrinsic instrument properties.
- Anchor the canonical score at the Issuer; allow instrument overlays (e.g., green bond flags).
- Support multiple providers, timestamps, and raw pillar subscores.
-Preserve methodology metadata (version, weights, controversy adjustments).

## Canonical YAML mapping

Below is a clean, canonical YAML mapping that fits naturally into a FinancialInstrument / Issuer ontology, supports multiple ESG providers, defines explicit inheritance rules, and allows instrument-level ESG overlays (e.g., green bonds, ESG funds).

The design principles:

- issuer-centric truth
- reference-data style
- time-versioned, provider-scoped facts
- non-destructive overrides at instrument level

### Conceptual positioning (short)

ESG is not an intrinsic instrument attribute.
It is assessment reference data, primarily attached to the Issuer, optionally augmented at Instrument level.

Issuer
 └── ESGAssessment (multi-provider, time-series)
       └── PillarScores (E/S/G)
            └── CompositeScore

FinancialInstrument
 └── ESGOverlay (optional)
       ├── InheritedIssuerAssessment (reference)
       └── InstrumentSpecificESG (overrides / additions)

### Canonical ESG data types

#### ESG provider reference

```yaml
ESGProvider:
  provider_id: string            # e.g. MSCI, Sustainalytics
  legal_name: string
  methodology_version: string
  rating_scale: string           # e.g. AAA–CCC, 0–100, risk-score
  website: uri
```

#### ESG pillar score

```yaml
ESGProvider:
  provider_id: string            # e.g. MSCI, Sustainalytics
  legal_name: string
  methodology_version: string
  rating_scale: string           # e.g. AAA–CCC, 0–100, risk-score
  website: uri
```

#### Composite ESG score

```yaml
ESGCompositeScore:
  score_value: number | string
  scale: string
  confidence_level: number       # optional
```

#### ESG assessment (provider + timestamp)

```yaml
ESGAssessment:
  assessment_id: string
  provider_ref: ESGProvider
  assessment_date: date
  coverage_scope: enum [issuer, instrument]
  methodology_version: string

  pillars:
    - ESGPillarScore
    - ESGPillarScore
    - ESGPillarScore

  composite:
    ESGCompositeScore

  controversies:
    level: enum [none, low, medium, high, severe]
    last_updated: date

  source:
    type: enum [reported, estimated, mixed]
    disclosure_year: integer
```

#### Issuer ontology (canonical ESG anchor)

```yaml
Issuer:
  issuer_id: string
  legal_name: string
  lei: string

  esg_assessments:
    - ESGAssessment
    - ESGAssessment
```

##### Example (issuer-level)

```yaml
issuer:
  issuer_id: ISSUER-CH-001
  legal_name: Example Energy AG
  lei: 5493001KJTIIGC8Y1R12

  esg_assessments:
    - assessment_id: MSCI-2024
      provider_ref: MSCI
      assessment_date: 2024-06-30
      coverage_scope: issuer
      methodology_version: "MSCI ESG 2024"

      pillars:
        - pillar: E
          score_value: AA
          scale: AAA–CCC
        - pillar: S
          score_value: A
          scale: AAA–CCC
        - pillar: G
          score_value: AAA
          scale: AAA–CCC

      composite:
        score_value: AA
        scale: AAA–CCC

      controversies:
        level: low
        last_updated: 2024-05-12

      source:
        type: mixed
        disclosure_year: 2023
```

#### FinancialInstrument ontology with ESG inheritance

##### Core rule (explicit)

```yaml
ESGInheritanceRule:
  default_behavior: inherit_from_issuer
  override_allowed: true
  override_scope: additive_only   # cannot erase issuer ESG
```

#### Instrument model

```yaml
FinancialInstrument:
  instrument_id: string
  instrument_type: string
  issuer_ref: Issuer

  esg_profile:
    inheritance_rule: ESGInheritanceRule

    inherited_assessments:
      from_issuer: true
      provider_priority:           # optional ordering
        - MSCI
        - Sustainalytics

    instrument_overlays:
      - ESGInstrumentOverlay
```

#### Instrument ESG overlay (key design)

```yaml
ESGInstrumentOverlay:
  overlay_type: enum [
    green_bond,
    social_bond,
    sustainability_bond,
    esg_fund,
    impact_product
  ]

  standard_reference:
    framework: enum [
      ICMA_GreenBondPrinciples,
      ICMA_SocialBondPrinciples,
      EU_GreenBondStandard
    ]

  use_of_proceeds:
    eligible_categories:
      - renewable_energy
      - clean_transport
    exclusion_categories:
      - fossil_fuels

  reporting_commitments:
    allocation_reporting: boolean
    impact_reporting: boolean

  instrument_specific_assessment:
    provider_ref: ESGProvider
    assessment_date: date
    score_adjustment: string | number
```

#### Example: Green bond inheriting issuer ESG

```yaml
financial_instrument:
  instrument_id: BOND-CH-2025-001
  instrument_type: green_bond
  issuer_ref: ISSUER-CH-001

  esg_profile:
    inheritance_rule:
      default_behavior: inherit_from_issuer
      override_allowed: true
      override_scope: additive_only

    inherited_assessments:
      from_issuer: true
      provider_priority:
        - MSCI

    instrument_overlays:
      - overlay_type: green_bond
        standard_reference:
          framework: ICMA_GreenBondPrinciples

        use_of_proceeds:
          eligible_categories:
            - renewable_energy
            - energy_efficiency
          exclusion_categories:
            - coal

        reporting_commitments:
          allocation_reporting: true
          impact_reporting: true

        instrument_specific_assessment:
          provider_ref: Sustainalytics
          assessment_date: 2025-01-15
          score_adjustment: "+10bps greenium"
```

### Design guarantees (why this works)

| Requirement            | Satisfied by            |
| ---------------------- | ----------------------- |
| Multi-provider support | `esg_assessments[]`     |
| Time-series ESG        | `assessment_date`       |
| Clear issuer primacy   | Issuer-anchored ESG     |
| Instrument specificity | `ESGInstrumentOverlay`  |
| Regulatory alignment   | ICMA / EU frameworks    |
| No data loss           | Additive override model |

### Strong recommendation (canonical rule)

- Never overwrite issuer ESG with instrument ESG.
- Instrument ESG is contextual, not corrective.


