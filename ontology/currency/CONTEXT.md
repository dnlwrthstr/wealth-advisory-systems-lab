# Currency – ISO 4217

This document describes how **currencies** are modeled and identified within the bank data securities domain.

Currencies are **not financial instruments** and are **not classified under ISO 10962 (CFI)**.
Instead, they are identified using the international standard **ISO 4217**, which provides a globally consistent representation of currencies used for pricing, settlement, valuation, accounting, and reporting.

---

## Standard

**ISO 4217 – Codes for the representation of currencies**

Maintained by the **International Organization for Standardization**, ISO 4217 defines:

* alphabetic currency codes (e.g. `EUR`, `USD`, `CHF`)
* numeric currency codes (e.g. `978`, `840`, `756`)
* minor unit information (number of decimal places)

---

## Purpose of ISO 4217

ISO 4217 answers the question:

> **“In which currency is this amount denominated?”**

It provides a **canonical, system-independent identifier** for currencies that is used consistently across:

* payment systems
* securities settlement
* trading and market data
* accounting and valuation
* regulatory and statistical reporting

---

## What ISO 4217 Represents

### Alphabetic Code

A three-letter code derived from the country code (ISO 3166) and the currency name.

Examples:

* `EUR` – Euro
* `USD` – US Dollar
* `CHF` – Swiss Franc

### Numeric Code

A three-digit numeric identifier, primarily used in legacy systems and messaging standards.

Examples:

* `978` – EUR
* `840` – USD
* `756` – CHF

### Minor Units

Defines the number of decimal places typically used.

Examples:

* `EUR` → 2 (cents)
* `USD` → 2 (cents)
* `JPY` → 0 (no minor unit)

---

## What ISO 4217 Is (and Is Not)

### What ISO 4217 *Is*

* A **global currency identifier**
* **Stable and deterministic**
* **Machine-readable**
* Independent of financial instruments or products

### What ISO 4217 *Is Not*

* Not a security classification (CFI)
* Not a country classification (ISO 3166)
* Not an exchange or trading venue identifier
* Not a pricing or FX rate source

---

## Role of Currency in the Securities Domain

In your domain model, **Currency is a foundational reference concept** used by multiple objects:

### Used By

* Financial instruments (nominal currency, issue currency)
* Market data (price currency, quotation currency)
* Cash balances and deposits
* Valuation and P&L calculations
* Settlement and payment flows

### Not a Financial Instrument

Currencies:

* are **not issued as securities**
* do **not have an issuer in the securities sense**
* do **not have listings or trading venues**
* do **not carry CFI codes**

They exist **outside the FinancialInstrument hierarchy**.

---

## Relationship to Other Standards

| Dimension         | Standard              |
| ----------------- | --------------------- |
| Currency          | **ISO 4217**          |
| Instrument type   | ISO 10962 (CFI)       |
| Issuer identity   | ISO 17442 (LEI)       |
| Trading venue     | ISO 10383 (MIC)       |
| Country           | ISO 3166              |
| Industry / sector | GICS / ICB / Telekurs |

ISO 4217 integrates cleanly with all of the above without overlap.

---

## Conceptual Model Placement

In the ontology:

* `Currency` is a **reference data entity**
* It is referenced by value objects (amounts, prices, balances)
* It is **not** part of the instrument inheritance tree

Conceptually:

```
MonetaryAmount
 ├─ amount
 └─ currency (ISO 4217)
```

---

## Example Representation

### YAML (Reference Data)

```yaml
currency:
  code: CHF
  numeric_code: 756
  name: Swiss Franc
  minor_units: 2
```

### Usage Example

```yaml
price:
  value: 102.35
  currency: CHF
```

---

## Summary

**ISO 4217 is the canonical standard for identifying currencies.**

In your architecture it:

* provides a clean separation between **money** and **securities**
* avoids misuse of CFI for non-securities
* ensures interoperability with payment, settlement, and accounting systems
* serves as the single source of truth for currency identification

This makes ISO 4217 a **core reference pillar** alongside CFI, LEI, and MIC in the overall securities domain model.
