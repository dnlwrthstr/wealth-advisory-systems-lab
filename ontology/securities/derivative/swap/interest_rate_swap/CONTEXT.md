# Interest Rate Swap (IRS) Specifications

## 1. Overview
An Interest Rate Swap is a derivative contract in which two parties exchange interest rate cash flows. The most common type is the **Fixed-for-Floating** swap, where one party pays a fixed rate and receives a floating rate (typically based on an index like SOFR or EURIBOR).

---

## 2. Core Swap Attributes
These attributes define the data structure for an interest rate instrument.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Notional Amount** | Decimal | The theoretical face value used to calculate interest payments (no principal is exchanged). |
| **Fixed Rate** | Decimal | The constant percentage rate paid by the fixed-leg party. |
| **Floating Index** | String | The reference rate for the floating leg (e.g., `LIBOR`, `SOFR`, `EURIBOR`). |
| **Spread** | Decimal | The constant percentage added to the floating index (e.g., SOFR + 0.10%). |
| **Payment Frequency**| Enum | How often payments occur (e.g., `MONTHLY`, `QUARTERLY`, `ANNUAL`). |

---

## 3. Contractual & Settlement Details
Based on standard derivative specifications.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Effective Date** | Date | The date interest starts accruing. |
| **Maturity Date** | Date | The final date when the swap obligations end. |
| **Settlement Type** | Enum | Almost exclusively `CASH` (net difference between legs). |
| **Day Count Conv.** | String | The method for calculating interest (e.g., `ACT/360`, `30/360`). |
| **Currency** | String | The ISO code for the cash flows (e.g., `USD`, `GBP`). |

---

## 4. Instrument Comparison: Swap vs. Future
Differences in how interest rate risk is managed.

| Feature | IR Future | IR Swap |
| :--- | :--- | :--- |
| **Trading Venue** | Regulated Exchange. | Over-the-Counter (OTC). |
| **Standardization** | Highly Standardized. | Custom/Bespoke. |
| **Obligation** | Mandatory for both. | Mandatory for both. |
| **Upfront Cost** | Initial Margin. | No upfront cost (typically). |
| **Counterparty Risk**| Minimal (Clearing House).| High (Direct/CSA dependent).|

---

## 5. Risk Factors
* **Interest Rate Risk:** The value of the swap changes as market interest rates fluctuate.
* **Credit Support:** Managed via **Credit Support Annex (CSA)** to mitigate counterparty default risk.
* **Tenor:** Unlike FX Spot (T+2), swaps are long-term commitments that can span 1 to 30+ years.