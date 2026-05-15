# Credit rating

**credit rating** is an independent, standardized assessment of the credit risk of a financial instrument. It expresses the likelihood that promised cash flows (interest and principal) will be paid in full and on time.

## What exactly is being rated?

Ratings apply to specific instruments, not just to issuers.

Typical rated instruments include:

- Bonds (sovereign, corporate, municipal)
- Notes and commercial paper
- Asset-backed and structured products (ABS, MBS, CDO tranches)
- Preferred securities

Each rating reflects the terms of that instrument (seniority, collateral, maturity, covenants), even when multiple instruments are issued by the same entity.

## Who assigns ratings?

Credit ratings are assigned by credit rating agencies (CRAs), primarily:

- [Moody’s](moody_s/CONTEXT.md)
- [S&P Global Ratings](s&p_global_rating/CONTEXT.md)
- [Fitch Ratings](fitch/CONTEXT.md)

These agencies are regulated (e.g., under EU CRA Regulation, SEC oversight in the US) and follow documented methodologies.

## The rating scale (high level)

Although symbols differ slightly, scales are broadly aligned.

### Investment grade

Low expected credit risk:

- AAA / Aaa – Highest quality
- AA / Aa – Very strong
- A / A – Strong
- BBB / Baa – Adequate (lowest investment grade)

### Speculative (high yield / junk)

Higher credit risk:

- BB / Ba
- B
- CCC / Caa
- CC / Ca
-C
- D – Default (missed payment)

Key boundary:
BBB- / Baa3 separates investment grade from speculative grade.

## How a rating is determined (process)

### Issuer analysis

Assessment of the obligor’s ability and willingness to pay:

- Business model and competitive position
- Financial metrics (leverage, coverage ratios, cash flow stability)
- Governance and management quality
- Macroeconomic and industry risks

### Instrument-specific analysis

Adjustments based on instrument structure:

- Seniority (senior secured vs subordinated)
- Collateral and recovery expectations
- Covenants
- Maturity
Structural subordination (e.g., holding company debt)

This is why two bonds from the same issuer can have different ratings.

### Committee decision

- Analysts present findings
- A rating committee votes
- The assigned rating is published with a rationale

## Ongoing monitoring

Ratings are not static.

Agencies continuously monitor:

- Earnings releases
- Covenant breaches
- M&A activity
- Macroeconomic shocks

Possible outcomes:

- Upgrade (credit profile improves)
- Downgrade (credit profile deteriorates)
- Outlook change (positive / negative / stable)
- Watchlist placement (short-term event risk)
- 
## Issuer rating vs instrument rating

| Concept                      | Meaning                                        |
| ---------------------------- | ---------------------------------------------- |
| Issuer (or corporate) rating | Overall default risk of the entity             |
| Instrument rating            | Default + recovery risk of a specific security |

Example:

- Issuer: BBB
- Senior unsecured bond: BBB
- Subordinated bond: BB+

## What ratings are used for

Ratings are embedded deeply in financial infrastructure:

- Portfolio construction (IG vs HY mandates)
- Risk management (credit limits, concentration rules)
- Regulation (Basel capital charges, Solvency II)
- Pricing (credit spreads vs risk-free rates)
- Eligibility (collateral at central banks, index inclusion)

Importantly: ratings are opinions, not guarantees.

## What ratings do not measure

Ratings do not assess:

- Market price volatility
- Liquidity
- Interest-rate risk
- FX risk
- Short-term trading performance

They focus narrowly on credit risk.

## Common misconceptions

- “AAA means risk-free” → False (only sovereigns approach this)
- “Downgrades cause defaults” → Correlation, not causation
- “All agencies always agree” → Methodologies differ

### Practical mental model

You can think of an instrument rating as answering:

*“If I hold this instrument to maturity, how confident should I be that I will receive all contractual payments?”*

Everything else—pricing, yield, regulation—builds on that answer.

## How do credit ratings map into Financial Instruments / Issuers?

Below is a clean, canonical YAML-style ontology mapping that separates Issuer credit quality from Instrument-level credit risk, aligns with industry practice, and fits naturally into a FinancialInstrument / Issuer domain model.

The structure is designed to be:

- Normalized
- Extensible to multiple rating agencies
- Compatible with regulatory, risk, and portfolio-use cases

### Core modeling principles

Key rules:

1. Issuer and Instrument ratings are distinct
2. Ratings are opinions issued by agencies
3. An instrument rating refines issuer risk via structure (seniority, collateral, recovery)
4. Ratings are time-versioned facts

### Issuer ontology - creditworthiness of the obligor

```yml
issuer:
  issuer_id: "CH001234567"
  legal_name: "Example Holding AG"

  credit_profile:
    issuer_ratings:
      - agency: "S&P"
        rating: "BBB+"
        rating_type: "issuer_credit_rating"
        outlook: "stable"
        scale: "long_term"
        date_assigned: "2025-03-15"
        status: "active"

      - agency: "Moody's"
        rating: "Baa1"
        rating_type: "issuer_credit_rating"
        outlook: "positive"
        scale: "long_term"
        date_assigned: "2025-02-10"
        status: "active"
```
### Financial instrument ontology - security-specific credit risk

```yaml
financial_instrument:
  instrument_id: "XS1234567890"
  instrument_type: "Bond"
  issuer_ref: "CH001234567"

  terms:
    currency: "CHF"
    maturity_date: "2030-06-30"
    coupon_type: "fixed"
    seniority: "senior_unsecured"
    collateral: false
    governing_law: "CH"

  credit_risk:
    instrument_ratings:
      - agency: "S&P"
        rating: "BBB"
        rating_type: "issue_credit_rating"
        scale: "long_term"
        outlook: "stable"
        date_assigned: "2025-03-15"
        status: "active"

      - agency: "Fitch"
        rating: "BBB"
        rating_type: "issue_credit_rating"
        scale: "long_term"
        date_assigned: "2025-03-20"
        status: "active"
```

Interpretation

- Rating reflects:
  - Issuer credit quality
  - Instrument seniority 
  - Expected recovery
-May differ from issuer rating

### Recovery and notching (optional but recommended)

```yml
credit_risk:
  recovery_assumptions:
    agency: "S&P"
    recovery_rating: "3"
    expected_recovery_percent: "50–70"
    methodology: "corporate_recovery"

  notching:
    base_issuer_rating: "BBB+"
    adjustment: "-1 notch"
    reason: "senior_unsecured_structure"
```

This enables:

- Explicit rating derivation
- Structured product modeling
- Transparency for auditors and regulators

### Rating scale reference (canonical dictionary)

```yml
rating_scales:
  long_term:
    investment_grade:
      - AAA
      - AA+
      - AA
      - AA-
      - A+
      - A
      - A-
      - BBB+
      - BBB
      - BBB-
    speculative_grade:
      - BB+
      - BB
      - BB-
      - B+
      - B
      - B-
      - CCC
      - CC
      - C
      - D

```

This allows:

- Validation
- Cross-agency normalization
- IG/HY classification logic

### Historical rating (time series support)

```yml
rating_history:
  - agency: "S&P"
    rating: "A-"
    date_from: "2022-01-01"
    date_to: "2024-12-31"

  - agency: "S&P"
    rating: "BBB+"
    date_from: "2025-01-01"
    date_to: null
```

### Regulatory & portfolio flags (derived attributes)

```yml
derived_credit_attributes:
  is_investment_grade: true
  regulatory_risk_weight:
    basel_iii: "50%"
    solvency_ii: "BBB_bucket"
  collateral_eligibility:
    central_bank: true
```

These are derived, never primary facts.

### Summary: canonical separation

| Layer                  | What it represents             |
| ---------------------- | ------------------------------ |
| Issuer.credit_profile  | Default risk of legal entity   |
| Instrument.credit_risk | Default + recovery of security |
| Rating agency          | Opinion provider               |
| Rating scale           | Normalized classification      |
| Derived attributes     | Regulatory / portfolio logic   |

### Strong recommendation

For robust implementation, we recommend:

1.  **Keep Primary and Derived Data Separate**: Always store the actual rating from the agency (e.g., "A-") and the date it was assigned. Do not rely solely on derived flags like `is_investment_grade` in the primary data store.
2.  **Explicit Agency Mapping**: Use a canonical mapping table to normalize ratings across different agencies (S&P, Moody's, Fitch) when performing portfolio-level analysis.
3.  **Support for Outlook and Watch**: Include `outlook` (stable, positive, negative) and `watch` status in your data model, as these are leading indicators of future rating changes.
4.  **Audit Trail**: Maintain a history of rating changes to support historical performance analysis and regulatory reporting.
5.  **Distinguish Issuer vs. Instrument**: Never assume an instrument's rating is the same as the issuer's rating. Always check for seniority and structural enhancements.

