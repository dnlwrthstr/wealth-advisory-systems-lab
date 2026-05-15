# Sttructured Product As A Concept

In professional finance, **Structured Products** (or Structured Notes) are modeled as "hybrid" instruments. They are essentially a combination of two or more financial components—typically a **debt instrument** (the bond) and one or more derivatives (like options).

To model them correctly in a system, you cannot use a single simple table. You must use a **multi-leg data model**.

## 1. The "Wrapper" Model

Structured products are often issued as debt, so they carry an ISIN and are categorized under the CFI Category: Debt (D), specifically **Group: Structured Instruments (Y)**.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Product Name** | String | e.g., "90% Capital Protected Note on SPI". |
| **ISIN / FIGI** | String | The global unique identifier for the security. |
| **Issuer** | String | The financial institution (e.g., UBS, Vontobel). |
| **Issue Price** | Decimal | Usually 100% of the Notional Amount. |
| **Capital Protection** | Percentage | The minimum amount returned at maturity (e.g., 90% or 100%). |

## 2. Component Modeling (The "Legs")

To value and manage risk, a system breaks the product down into its constituent parts:

### Leg A: The Fixed Income Component

This is the "Zero-Coupon Bond" portion. The issuer takes a part of your money and invests it so that it grows back to the "Capital Protection" level by the maturity date.

- **Model Type**: BOND.md
- **Key Field**: Discount Rate / Accrual Yield.

### Leg B: The Derivative Component

The remaining money is used to buy options on an **Underlying Asset** (like the SPI or a basket of stocks). This provides the "upside" or "bonus" return.

- **Model Type**: OPTIONS.md
- **Key Field**: Participation Rate (e.g., you get 150% of the index's growth).

## 3. Payoff Logic (The "Engine")

Since structured products have "if/then" scenarios, the data model must include **Triggers** or **Barrier** logic.

| Feature | Data Type | Description |
| :--- | :--- | :--- |
| **Barrier Level** | Decimal | The price level that, if hit, changes the payoff (e.g., "Knock-in"). |
| **Observation Date** | Date | When the system checks if the barrier was hit. |
| **Cap / Floor** | Decimal | The maximum or minimum possible return. |
| **Autocall Level** | Decimal | The level at which the product is automatically "called" and settled early. |

## 4. Institutional Risk Modeling

For professional clients, modeling includes Counterparty Risk because structured products are unsecured obligations of the issuer. If the bank fails, the "Capital Protection" fails too.

- **Credit Linkage**: The model must link to the **Credit Rating** of the issuer.
- **Liquidity Flag**: Usually marked as **Low Liquidity** since these are often "buy-to-hold" instruments.

## 5. Regulatory Compliance

Structured products are subject to various regulations, including Basel III and MiFID II. The data model must include fields for regulatory compliance, such as:

| Feature | Data Type | Description |
| :--- | :--- | :--- |
| **Regulatory Classification** | String | e.g., "Complex Derivative". |
| **Reporting Requirements** | Boolean | Indicates if the product must be reported to regulators. |
| **Capital Requirements** | Decimal | The amount of capital required to support the product. |

