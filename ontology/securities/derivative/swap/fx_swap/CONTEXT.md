# FX Swap Data Model & Specifications

## 1. Overview
An FX Swap consists of two "legs": a **Spot** transaction (near leg) and a **Forward** transaction (far leg) executed simultaneously.

---

## 2. Core FX Swap Attributes
These attributes define the specific financial data required to represent an FX Swap contract.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Near Amount** | Decimal | The amount of the first currency to be exchanged in the near leg. |
| **Near Currency** | String | The ISO 4217 code for the base currency (e.g., `USD`). |
| **Forward Rate** | Decimal | The agreed-upon exchange rate for the future date (far leg). |
| **Value Date** | Date | The date of the final payment/exchange (Maturity). |
| **Credit Support** | Enum | Links to collateral or margin requirements (e.g., `CSA_AGREEMENT`). |

---

## 3. FX Market Comparison: Spot vs. Forward
Understanding the components that make up the swap legs.

| Feature | FX Spot | FX Forward |
| :--- | :--- | :--- |
| **Settlement Date** | Typically T+2 (2 business days). | Any date beyond T+2. |
| **Rate Basis** | Current Market Price (Spot Rate). | Spot Rate ± Forward Points (Interest diff). |
| **Purpose** | Immediate Liquidity/Exchange. | Hedging future cash flows/Risk Mgmt. |

---

## 4. Derived Contract Specifications
General attributes inherited from the underlying derivative structure.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying Asset** | String | The reference currency pair (e.g., USD/JPY, EUR/USD). |
| **Maturity Date** | Date | The final date for the far-leg delivery. |
| **Settlement Type** | Enum | Usually `CASH` or `PHYSICAL` exchange of currencies. |
| **Currency** | String | The ISO code for the contract pricing. |

---

## 5. Technical Implementation Notes
* **Standardization:** Unlike Futures, FX Swaps are often traded **Over-the-Counter (OTC)**, meaning they are bespoke and have higher counterparty risk.
* **Liquidity:** FX Swaps generally have lower liquidity than exchange-traded futures, making them more difficult to cancel once initiated.
* **Counterparty Risk:** Regulated by **Credit Support Annex (CSA)** agreements to manage the direct relationship risk between parties.