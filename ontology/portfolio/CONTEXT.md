# Portfolio

This document describes the core `Portfolio` entity and its role within the broader Portfolio Domain ontology.

## Portfolio Ontology Overview

The Portfolio Domain serves as the central hub for managing client investment portfolios. It encapsulates various aspects related to financial holdings, their associated accounts, and the activities that affect them. The overall ontology within this domain connects:

*   **Portfolios**: The top-level aggregation of client assets.
*   **Accounts**: Specific cash and safekeeping accounts linked to a portfolio.
*   **Transactions**: All financial movements, including trades, corporate actions, and cash flows.
*   **Valuated Positions**: The current state and value of holdings within the portfolio.
*   **Customer**: The individual or entity owning the portfolio.
*   **Performance Metrics**: Data points for evaluating portfolio performance.

## `portfolio.yml` - The Core Portfolio Definition

The `portfolio.yml` file defines the fundamental structure and key characteristics of a `Portfolio` within the system.

### `PortfolioInformation` Entity

This entity represents the essential details of a portfolio:

*   **`identification`**: A mandatory string that serves as a unique and unambiguous identifier for the portfolio. This ID facilitates communication and referencing between the portfolio owner and the portfolio servicer.
    *   **Type**: `string`
    *   **Constraints**: Minimum length 1, maximum length 128.
    *   **Example**: `87654-3219`

*   **`referenceCurrency`**: Specifies the primary currency in which the portfolio's performance and value are typically reported or measured. This property links to the `Currency` entity defined in `FinancialInstrumentBase.yml` within the `securities_domain`.
    *   **Type**: Reference to `Currency` (`../securities_domain/financial_instruments/FinancialInstrumentBase.yml#/ontology/entities/Currency`)

---
*This page provides context for the Portfolio Domain and specifically details the `portfolio.yml` definition.*