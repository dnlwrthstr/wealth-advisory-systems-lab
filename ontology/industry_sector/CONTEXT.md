# Industry / Sector  Classification

## Purpose of Industry and Sector Classifiers

Industry and sector identifiers serve to categorize financial instruments and their issuers based on their primary economic activity. This classification is essential for:

- **Portfolio Construction & Diversification**: Ensuring exposure is spread across different economic sectors to mitigate risk.
- **Risk Management**: Identifying concentration risks in specific industries.
- **Performance Benchmarking**: Comparing the performance of an investment against its industry peers.
- **Regulatory Reporting**: Meeting requirements for disclosing sector-level breakdowns of holdings.
- **Investment Strategy**: Implementing sector-rotation strategies or thematic investing.

## Classification Standards

This directory contains definitions and modeling patterns for several widely used classification standards:

- **[GICS (Global Industry Classification Standard)](gics/CONTEXT.md)**
  Maintained by MSCI and S&P Dow Jones Indices. The de facto global standard for equity markets.
- **[ICB (Industry Classification Benchmark)](icb/CONTEXT.md)**
  Maintained by FTSE Russell. Widely used in European and global markets.
- **[Telekurs Classification](telekurs/CONTEXT.md)**
  Maintained by SIX Financial Information. The standard for the Swiss financial market.
- **[Canonical Model](canonical/CONTEXT.md)**
  Defines the generic structure for representing any classification system, node, and assignment within the ontology.

> These are **commercial classification standards**, not ISO standards.

## What You Get

- **Sector classification** (e.g. Energy, Financials, Information Technology)
- **Industry and sub-industry classification**
- **Indirect regional exposure**, derived via issuer domicile and revenue geography mapping

## Used For

- **Portfolio construction**  
  Sector allocation, diversification, and benchmarking

- **Risk attribution**  
  Sector-driven performance and factor analysis

- **Regulatory disclosures**  
  Sector breakdowns required for client reporting and regulatory filings

## Notes

- GICS and ICB classify **economic activity**, not legal domicile.
- Regional exposure is typically inferred by combining:
  - Issuer country (e.g. LEI / registered domicile)
  - Revenue or operating geography (if available)
- Coverage, depth, and licensing terms differ between GICS and ICB.
