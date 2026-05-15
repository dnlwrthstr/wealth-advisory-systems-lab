# Global Industry Classification Standard (GICS)

## Overview

The **Global Industry Classification Standard (GICS)** is a widely used framework for classifying companies according to their **primary business activity**.  
It was jointly developed and is maintained by **MSCI** and **S&P Dow Jones Indices**.

GICS is a **commercial, non-ISO standard** and is the dominant sector classification system used in global equity markets.

## Purpose of GICS

GICS provides a **consistent and hierarchical structure** to:

- Classify companies by **economic activity**
- Enable **sector-based analysis** across markets
- Support **portfolio construction, benchmarking, and risk analysis**
- Standardize **reporting and disclosures**

## GICS Hierarchical Structure

GICS uses a **four-level hierarchy**, from broad sectors to granular sub-industries.

| Level | Description | Example |
|-----|------------|--------|
| **Sector** | Broad economic sector | Information Technology |
| **Industry Group** | Related industries | Software & Services |
| **Industry** | Specific business area | Software |
| **Sub-Industry** | Most granular level | Application Software |

Each level has a **numeric code**, forming a stable identifier.

Example:

45 Information Technology

4510 Software & Services

451030 Software

45103010 Application Software

## Classification Principle

- Each company is assigned **one primary GICS classification**
- Classification is based on:
  - Primary source of revenue
  - Business model
  - Market perception
- Conglomerates are classified by **dominant revenue contribution**

GICS reflects **what a company does**, not:
- Where it is incorporated
- Where it is listed
- Where it trades

## Regional Information in GICS

GICS itself is **region-agnostic**.

Regional exposure is obtained by **combining GICS with issuer data**, such as:

- Issuer domicile (e.g. LEI country)
- Headquarters location
- Revenue or operating geography (if available)

This separation ensures:
- Clean economic classification (GICS)
- Independent geographic modeling (issuer / revenue data)

## Typical Use Cases

### Portfolio Construction
- Sector allocation and diversification
- Index construction and comparison

### Risk Attribution
- Sector-based performance decomposition
- Factor and macro exposure analysis

### Regulatory & Client Reporting
- Sector breakdowns in factsheets
- Risk disclosures and suitability reporting

## Governance and Maintenance

- Maintained by **MSCI** and **S&P Dow Jones Indices**
- Periodically reviewed and updated
- Sector definitions may evolve to reflect:
  - Technological change
  - New industries
  - Structural shifts in the economy

Changes are communicated in advance to market participants.

## Key Characteristics

- Global and equity-focused
- Commercially licensed
- Widely adopted by:
  - Asset managers
  - Index providers
  - Risk and analytics platforms
- Stable codes with controlled evolution

## Summary

GICS is the **de facto global standard** for sector and industry classification in financial markets.  
It enables consistent economic analysis while remaining independent from legal, trading, or regional attributes of financial instruments.

## Modeling Notes (Best Practice)

- GICS is pure reference data

- Do not encode regional information inside GICS

- Geography belongs to:

  - Issuer (LEI, domicile)

  - Revenue / operating exposure models

- Codes are stable identifiers and should be treated as immutable keys

- This structure maps cleanly to:

  - Relational schemas

  - Graph models (Sector → IndustryGroup → Industry → SubIndustry)

  - OpenSearch / Elasticsearch reference indices
