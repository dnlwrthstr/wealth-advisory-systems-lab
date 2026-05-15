# Barrier Reverse Convertible

A **Barrier Reverse Convertible (BRC)** is one of the most popular structured products for institutional and professional clients, particularly in yield-enhancement strategies. It is modeled as a **fixed-income instrument** (bond) combined with a **sold (written) down-and-in put option**.


## 1. Overview

A BRC offers a guaranteed coupon regardless of the underlying asset's performance. However, the repayment of the full principal is "conditional": if the underlying asset breaches a specific Barrier Level, the investor may receive the physical asset (or its cash equivalent) at a loss instead of the principal.

## 2.  Core Product Attributes

These fields define the "wrapper" and the fixed-income component.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **ISIN** | String | The unique security identifier. |
| **Coupon Rate (p.a.)** | Decimal | The guaranteed annual interest payment (paid regardless of barrier). |
| **Denomination** | Decimal | The face value per unit (e.g., 1,000 USD). |
| **Issuer** | String | The financial institution guaranteeing the product. |
| **Maturity Date** | Date | The final date of the contract and principal repayment. |

## 3. Derivative & Barrier Attributes

This section models the "conditional" risk—the short put option component.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying Asset** | String | The reference asset (e.g., SPI Index, Apple Stock). |
| **Strike Price** | Decimal | Usually 100% of the initial fixing price. |
| **Barrier Level** | Decimal | The "safety" threshold (e.g., 60% or 75% of initial price). |
| **Barrier Type** | Enum | `CONTINUOUS` (anytime) or `EUROPEAN` (only at maturity). |
| **Barrier Event** | Boolean | System flag: `TRUE` if the barrier has been breached. |
| **Settlement Type** | Enum | `CASH` or `PHYSICAL` (delivery of shares). |

## 4. Payoff Logic for your Notebook

The modeling engine evaluates the following logic at the **Maturity Date**:

### 1. **Scenario A (Safe)**: The Underlying Asset never touched the barrier during the observation period.

> **Result**: Investor receives 100% Principal + Coupon.

### 2. **Scenario B (Recovery**): The Barrier was touched, but the price recovered and ended above the Strike Price.

> **Result**: Investor receives 100% Principal + Coupon.

### 3. Scenario C (Loss): The Barrier was touched, and the price ended below the Strike Price.

> Result: Investor receives the **Underlying Asset** (Physical) or Cash equivalent to the dropped price + Coupon. (Loss of principal).

### 5. Institutional Implementation Notes

- *Credit Risk*: Professional clients must model the Issuer's Credit Spread. If the issuer goes bankrupt, the coupon and principal protection are lost.

- **Volatility Sensitivity (Vega)**: Since the investor is "short" a put option, a rise in market volatility generally decreases the value of the BRC before maturity.

- **CFI Code**: Typically DY\*\*\*\* (Debt Instrument, Structured).


