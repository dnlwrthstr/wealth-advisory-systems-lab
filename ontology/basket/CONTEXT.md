# Basket Definition & Component Model

## 1. Overview
A Basket Definition is a reference data structure that groups multiple underlying assets (Equities, Indices, or Commodities) into a single logical entity. This is used to calculate "Worst-of" performance, "Best-of" performance, or weighted average returns.

## 2. Basket Header Attributes
These attributes define the collection as a whole.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Basket ID** | UUID | Unique identifier used to link the basket to a structured product. |
| **Basket Type** | Enum | `WORST_OF`, `BEST_OF`, `WEIGHTED_AVERAGE`, or `EQUAL_WEIGHTED`. |
| **Currency** | String | The base currency of the basket (usually matching the product). |
| **Rebalancing** | Enum | `STATIC` (fixed components) or `DYNAMIC` (periodic updates). |
| **Constituent Count**| Integer | Total number of assets in the basket. |

## 3. Constituent Attributes (The Components)
Each asset within the basket requires its own data row to track performance.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying ID** | String | The ticker or ISIN of the individual component. |
| **Initial Fixing** | Decimal | The reference price of the asset at the start of the contract. |
| **Weight** | Decimal | The percentage of the basket this asset represents (e.g., 0.33). |
| **Barrier Level** | Decimal | The specific price threshold for this component (e.g., 60% of fixing). |
| **Current Performance**| Decimal | Calculated as: `(Current Price / Initial Fixing)`. |


## 4. Multi-Asset Correlation Matrix
For institutional risk management, the relationship between basket members is modeled here.

| Asset A | Asset B | Correlation Coefficient | Risk Impact |
| :--- | :--- | :--- | :--- |
| **AAPL** | **MSFT** | +0.85 | High Correlation (Low Coupon) |
| **AAPL** | **GOLD** | -0.10 | Low Correlation (High Coupon) |


## 5. Implementation Notes for Professional Clients
* **Corporate Actions:** The model must account for stock splits or dividends affecting individual **Initial Fixing** prices.
* **Currency Risk (Quanto):** If basket members are in different currencies (e.g., USD and CHF), the model must specify if the performance is "Quanto" (shielded from FX risk).
* **Worst-of Trigger:** In a Multi-BRC, if the **Current Performance** of *any* constituent drops below its **Barrier Level**, a global `Barrier_Breach` flag is triggered for the linked product.