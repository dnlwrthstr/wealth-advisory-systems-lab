# ICB (Industry Classification Benchmark) — FTSE Russell

**Industry Classification Benchmark (ICB)** is a proprietary, hierarchical industry classification system developed and maintained by FTSE Russell. It is widely used across European and global capital markets, particularly in conjunction with FTSE equity indices.

#### Purpose and Scope

ICB provides a standardized framework for categorizing companies based on their primary business activity. The classification supports consistent analysis of industries and sectors across markets, enabling comparability between issuers, indices, and portfolios.

#### Structure

ICB is organized as a four-level hierarchy:

1. **Industry** (broadest level)
2. **Supersector**
3. **Sector**
4. **Subsector** (most granular level)

Each issuer is assigned to exactly one ICB subsector based on its dominant revenue-generating activity.

#### What You Get

* Consistent **sector and industry classifications** for issuers
* Granular **subsector-level taxonomy** suitable for detailed analysis
* Alignment with FTSE index construction methodologies

#### Regional Exposure

ICB itself is **region-agnostic**. Geographic or regional exposure is derived indirectly by linking the classified issuer to:

* Issuer domicile or headquarters (e.g. via LEI country)
* Listing or trading venue region
* Geographic revenue breakdowns, where available

#### Used For

* Equity index construction and maintenance
* Portfolio construction and sector allocation
* Risk attribution and performance analysis
* Regulatory and client disclosures requiring industry breakdowns

#### Standardization Note

ICB is a **commercial, proprietary classification standard** and is not governed by ISO. Usage and redistribution are subject to FTSE Russell licensing terms.

#### Modeling Implications

In a financial instrument or issuer data model, ICB is typically represented as:

* A **classification reference** attached to the *Issuer*
* A **time-versioned attribute** to support reclassifications
* A **hierarchical controlled vocabulary** (Industry → Subsector)

ICB complements — but does not replace — regional identifiers such as LEI country, MIC, or currency region.

### Example — Issuer with ICB Classification

```yaml
issuer:
  issuer_id: "CH0001234567"
  name: "Example Bank AG"
  lei: "5493001KJTIIGC8Y1R12"
  domicile_country: "CH"

  industry_classification:
    system: "ICB"
    provider: "FTSE Russell"
    effective_date: "2024-01-01"

    industry:
      code: "8000"
      name: "Financials"

    supersector:
      code: "8300"
      name: "Banks"

    sector:
      code: "8350"
      name: "Banks"

    subsector:
      code: "8355"
      name: "Diversified Banks"
```

### Interpretation

* The issuer is classified **once** at the most granular level (Subsector).
* Higher levels (Sector, Supersector, Industry) are **derived from the hierarchy**, not assigned independently.
* No regional information is embedded in ICB itself.
* Regional exposure is obtained by joining:

  * `issuer.domicile_country`
  * listing MICs
  * revenue geography (if modeled elsewhere)

### Why This Works Well

* Clean separation of **classification** vs **region**
* Supports **time-versioning** (reclassifications)
* Aligns with portfolio, risk, and regulatory reporting use cases
* Maps directly to GICS if a crosswalk is added later
