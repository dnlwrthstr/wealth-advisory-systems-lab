# Finfox Ontology

This ontology defines the data structures and relationships for a comprehensive financial services platform. It is organized into several domains, each focusing on a specific area of banking and investment services.

## Setting the Scene

This document provides a high-level overview of the Financial Services Data Model Ontology. The ontology is designed to capture the complex relationships and data structures within the platform.

### High-Level Component Diagram

The following diagram illustrates the high-level components of the platform and how they interact.

![High Level Component Diagram](img/high_level_component_diagram.svg)

### Ontology Domains

The ontology is organized into the following folders:

*   **[Asset Class](asset_classes/CONTEXT.md)**
*   **[Basket Definition](basket/CONTEXT.md)**
*   **[CFI (Classification of Financial Instruments)](reference_data/cfi/CONTEXT.md)**
*   **[Commodities](commodities/CONTEXT.md)**
*   **[Crypto Assets](crypto_assets/CONTEXT.md)**
*   **[Currency – ISO 4217](currency/CONTEXT.md)**
*   **[Index](index/CONTEXT.md)**
*   **[Industry / Sector Classification](industry_sector/CONTEXT.md)**
*   **[Financial Instruments Base](instrument_base/CONTEXT.md)**
*   **[Issuance](issuance/CONTEXT.md)**
*   **[Issuer](issuer/CONTEXT.md)**
*   **[Loans](loans/CONTEXT.md)**
*   **[Market Data](market_data/CONTEXT.md)**
*   **[Overlay](overlay/CONTEXT.md)**
*   **[Partner](partner/CONTEXT.md)**
*   **[Portfolio](portfolio/CONTEXT.md)**
*   **[Rating](rating/CONTEXT.md)**
*   **[Regulatory](regulatory/CONTEXT.md)**
*   **[Securities](securities/CONTEXT.md)**
*   **[Third Party Assets](third_party_assets/CONTEXT.md)**
*   **[Trading Venue](trading_venue/CONTEXT.md)**
*   **[User](user/CONTEXT.md)**

### Purpose of the Ontology

The primary goal of this ontology is to provide a standardized, machine-readable representation of financial data that can be used across different modules of the platform, ensuring consistency between:

1.  **Documentation**: Automatically generated diagrams and descriptions.
2.  **Glossary**: A comprehensive [Glossary of Terms](../GLOSSARY.md) used in the model.
3.  **API Specifications**: Derived OpenAPI schemas (e.g., Open Wealth).
3.  **Persistence**: Mapping to database schemas (e.g., Neo4j).
4.  **Validation**: Type-safe data handling in Pydantic models.

---
*This page is automatically generated from the ontology definition.*
