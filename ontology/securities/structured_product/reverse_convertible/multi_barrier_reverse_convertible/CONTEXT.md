# Multi Barrier Reverse Convertible - Multi-BRC

## 1. Overview

In a Multi-BRC, the investor receives a fixed coupon, but the principal protection depends on all assets in a basket. If any single asset in the basket touches its barrier, the protection is lost for the entire product, and repayment is determined by the asset with the worst performance at maturity.

## 2. Core Product Attributes

These attributes define the high-level structure of the multi-asset note.

| Attribute              | Data Type | Description |
|:-----------------------| :--- | :--- |
| **ISIN**               | String | Global identifier for the structured note. |
| **Basket**             | UUID | Links to the [Basket Definition](../../../../basket/CONTEXT.md) containing the individual assets. |
| **Coupon Rate (p.a.)** | Decimal | Typically higher than a single-asset BRC due to increased risk. |
| **Issuer**             | String | The entity responsible for the fixed coupon and principal return. |
| **Maturity Date**      | Date | The final settlement date. |

## 3. "Worst-Of" & Basket Attributes

This section models the specific institutional logic for multi-asset derivatives.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Worst-of Logic** | Boolean | Set to `TRUE` (Standard for Multi-BRCs). |
| **Barrier Level** | Decimal | Usually expressed as a % of the Initial Fixing (e.g., 55%). |
| **Correlation Factor** | Decimal | The statistical relationship between basket assets (critical for valuation). |
| **Strike Price** | Decimal | The reference price for each asset (usually 100% of start price). |
| **Physical Delivery** | Enum | If triggered, identifies which asset is delivered (usually the "Worst Performer"). |

## 4. Payoff Logic: The "Worst-Of" Calculation

The modeling engine must track the performance ($P$) of every asset ($i$) in the basket:

$$
P_i = \frac{\text{Current Price}_i}{\text{Initial Fixing}_i}
$$

### At Maturity:

1. **If no asset touched its barrier**: Investor receives 100% Principal + Coupon.
2. **If ANY asset touched its barrier**: If the Worst Performer ($min(P_i)$) is $\ge$ 100%:
  Investor still receives 100% Principal + Coupon.
  - If the **Worst Performer** ($min(P_i)$) is $<$ 100%: Investor receives the **Worst Performer's** value (Cash or Shares) + Coupon.

## 5. Institutional Risk: Correlation Risk

For professional clients, the primary risk isn't just the individual stocks, but **Correlation Risk**:

- **High Correlation**: If all stocks move together, the risk is similar to a single-asset BRC.
- **Low Correlation**: If stocks move independently, the chance of **one** of them hitting a barrier increases significantly, which is why these products offer much higher coupons.
- **CFI Code: Typically** DY\*\*\*\* (Debt, Structured).
