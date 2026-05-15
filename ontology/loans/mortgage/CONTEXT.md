# Mortgage Loan Data Model & Specifications

## 1. Overview
A mortgage is a debt instrument, secured by the collateral of specified real estate property, that the borrower is obliged to pay back with a predetermined set of payments.

## 2. Core Mortgage Attributes
These attributes define the primary financial characteristics of the loan.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Notional Amount** | Decimal | The face value or original principal amount of the loan. |
| **Interest Rate** | Decimal | The percentage rate charged on the loan (Fixed or Floating). |
| **Maturity Date** | Date | The final date when the total principal and interest must be settled. |
| **Currency** | String | The ISO 4217 code for the loan payments (e.g., `USD`). |
| **Credit Support** | Enum | Links to the collateral/security agreement (the property deed). |

## 3. Repayment & Technical Specifications
Details regarding the structure of the debt service.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying Asset** | String | The legal description or ID of the property acting as collateral. |
| **Payment Frequency**| Enum | The schedule of payments (e.g., `MONTHLY`). |
| **Settlement Type** | Enum | Typically `CASH` payments resulting in the eventual release of lien. |
| **Initial Margin** | Decimal | Often referred to as the "Down Payment" in a mortgage context. |
| **Amortization Type** | Enum | The method of principal reduction (e.g., `LINEAR`, `BULLET`). |

## 4. Market Comparison: Mortgage vs. Futures
Understanding the difference between a private debt contract and an exchange-traded instrument.

| Feature | Mortgage (Private Debt) | Interest Rate Future |
| :--- | :--- | :--- |
| **Trading Venue** | Over-the-Counter (OTC) / Private. | Regulated Exchange. |
| **Standardization** | Custom/Bespoke per borrower. | Highly Standardized. |
| **Liquidity** | Low (Difficult to exit/sell). | High (Easy to exit). |
| **Counterparty Risk** | High (Direct Borrower/Lender). | Minimal (Clearing House). |
| **Obligation** | **Mandatory** for both parties. | **Mandatory** for both parties. |

## 5. Risk & Implementation Notes
* **Collateral Risk:** Since the loan is secured, the lender has a claim on the **Underlying Asset** if the borrower fails to meet the **Obligation**.
* **Prepayment Risk:** Unlike standard **Futures**, mortgages often allow the borrower to settle the **Notional Amount** early, affecting the expected interest yield.
* **Tick Size/Pricing:** While not traded in "ticks" like exchange instruments, the interest rate is usually sensitive to 1/8th or 0.01 percentage point increments.