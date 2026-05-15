# Total Return Swap (TRS) Specifications

## 1. Overview
A Total Return Swap is a derivative contract where one party (the Total Return Receiver) receives the income and capital gains of an underlying asset, while the other party (the Total Return Payer) receives a set rate (fixed or floating).

## 2. Core TRS Attributes
These attributes define the data structure for the total return exchange.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying ID** | String/UUID | The specific asset being swapped (e.g., a stock, bond, or index). |
| **Notional Amount** | Decimal | The face value of the underlying asset protected or swapped. |
| **Funding Rate** | Decimal | The set rate paid to the payer (e.g., SOFR + Spread). |
| **Payment Frequency**| Enum | How often the total return and funding legs are settled. |
| **Asset Performance**| Decimal | The capital gains/losses plus any income (dividends/coupons) generated. |

## 3. Contractual & Settlement Details
Standardized attributes for the execution of the swap.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Maturity Date** | Date | The final date the contract remains valid. |
| **Settlement Type** | Enum | Usually `CASH` (price difference payout). |
| **Initial Margin** | Decimal | The "down payment" or collateral required to open the position. |
| **Currency** | String | The ISO code for the cash flows (e.g., `USD`, `EUR`). |
| **Credit Support** | Enum | Links to the `CSA_AGREEMENT` for collateral management. |

## 4. Market Comparison: TRS vs. Futures
How a TRS differs from standard exchange-traded instruments.

| Feature | Equity Future | Total Return Swap |
| :--- | :--- | :--- |
| **Trading Venue** | Regulated Exchange. | Over-the-Counter (OTC). |
| **Standardization** | Highly Standardized. | Custom/Bespoke. |
| **Counterparty Risk**| Minimal (Clearing House).| High (Direct relationship).|
| **Income** | Usually reflected in price. | Direct pass-through of dividends/interest. |

## 5. Technical Implementation Notes
* **Exposure:** The Receiver gains full exposure to the **Underlying Asset** without having to own it on their balance sheet.
* **Obligation:** Unlike options, a TRS is **Mandatory** for both parties to fulfill until the **Maturity Date**.
* **Risk:** The Receiver faces "theoretically unlimited" risk if the underlying asset price drops significantly.

## Key Insight

In a TRS, the **Total Return Receiver** is effectively "Long" the asset, while the **Total Return Payer** is effectively "Short" the asset or hedging their existing physical holding.
