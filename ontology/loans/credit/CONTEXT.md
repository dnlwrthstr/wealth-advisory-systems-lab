# Credit (Lending and Liabilities) in a Portfolio Context

In wealth management, a Credit (or Loan) position represents a liability—money the client owes to the bank or a third party. While most securities (stocks, bonds, funds) are assets, credit is the "negative" side of the balance sheet. It is often used strategically to provide liquidity without selling off long-term investments.

## Common Types of Credit Positions

### Common Loan Types and Use Cases

| Type | Description | Common Use Case |
| :--- | :--- | :--- |
| **Lombard Loan** | A loan secured by the securities in the portfolio (stocks/bonds). | "Borrowing against your portfolio" to buy more assets or get cash. |
| **Mortgage** | A loan secured by real estate property. | Purchasing property or refinancing real estate. |
| **Fixed-Term Loan** | A loan with a set maturity date and a fixed interest rate. | Large, planned capital expenditures. |
| **Current Account Overdraft** | A flexible, unsecured line of credit on a cash account. | Short-term liquidity for daily expenses. |
| **Guarantee / LC** | A bank’s commitment to pay a third party if the client fails to do so. | Business transactions or security deposits. |

## How Credit Works in a Portfolio

Credit is measured by its Principal (the amount borrowed) and its Cost (the interest rate).

- **Principal Amount**: The original amount borrowed.
- **Current Balance**: The amount currently outstanding, which may include capitalized interest.
- **Collateral (The "Security")**: Most professional credit is "Secured." This means if the borrower doesn't pay, the bank can seize the assets (like stocks or a house) to cover the debt.
- **Loan-to-Value (LTV)**: This is the critical ratio of the loan amount divided by the value of the collateral.
    - Example: A $500,000 loan against a $1,000,000 portfolio has an LTV of 50%.

## Why Use Credit?

1. **Leverage**: Using borrowed money to invest more, potentially magnifying returns (though this also magnifies losses).
2. **Tax Efficiency**: In many regions, selling stocks triggers "Capital Gains Tax." Borrowing against them allows for liquidity without a "taxable event."
3. **Bridge Financing**: Covering a short-term cash need while waiting for a larger payment to arrive.

## Key Values for Modeling a Credit Instrument

When modeling a loan as an instrument in a system like OpenWealth, you need the following attributes:

### 1. Loan Terms

- **Interest Rate**: The percentage charged (e.g., 4.5%).
- **Rate Type**: FIXED (constant), FLOATING (linked to a benchmark like LIBOR/SOFR), or TIERED.
- **Maturity Date**: When the full principal must be repaid.
- **Repayment Schedule**: BULLET (all at the end), AMORTIZING (regular installments), or INTEREST_ONLY.

### 2. The Interest Calculation

- **Accrued Interest**: The interest that has built up since the last payment.
- **Day Count Convention**: The math used to calculate daily interest (e.g., 30/360 or ACT/360).
- **Payment Frequency**: How often the interest is billed (Monthly, Quarterly, Annually).

### 3. Monitoring & Risk

- **LTV Ratio**: The current health of the loan.
- **Margin Call Level**: The LTV threshold where the bank requires the client to add more collateral or sell assets to pay down the loan.
- **Limit: The maximum amount the client is allowed to borrow.

## Risks of Credit Positions

### Interest Rate Risk

If a loan has a "floating" rate, and central banks raise interest rates, the cost of the loan increases, potentially squeezing the borrower's cash flow.

### Margin Call Risk

If the value of the collateral (e.g., the stock market) drops significantly, the LTV rises. If it hits the "Margin Call" level, the bank may force the sale of the assets at the worst possible time (the market bottom) to protect its loan.

### Liquidity Risk

Unlike a stock, you cannot simply "sell" a loan. Repaying a fixed-term loan early often results in a **Prepayment Penalty**.

## Technical Data Model (JSON Example)

In a portfolio view, credit is often displayed as a negative value to offset the total Net Worth.

```json
{
  "instrument_id": "LOAN-7721-CH",
  "type": "CREDIT",
  "sub_type": "LOMBARD_LOAN",
  "currency": "CHF",
  "principal_amount": 250000.00,
  "interest_rate": 0.0325,
  "rate_type": "FLOATING",
  "benchmark": "SARON",
  "maturity_date": "2028-12-31",
  "collateral_ids": ["PORTFOLIO-9921"],
  "current_ltv": 0.42,
  "margin_call_threshold": 0.65
}
```

## Credit as a Security

To model a Credit instrument accurately within a financial system, you must capture the contractual obligations, the cost of capital, and the risk mitigation (collateral) parameters.

Unlike a stock or a bond, a credit instrument is often a liability for the client, requiring specific fields to track repayment schedules and interest accruals.

### 1. Core Contractual Attributes

These attributes define the "who, what, and when" of the debt.

### Loan Data Attributes

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Principal Amount** | Decimal | The total amount borrowed (the original debt). |
| **Currency** | String | ISO 4217 code (e.g., `USD`, `CHF`). |
| **Start Date** | Date | The date the funds were disbursed to the borrower. |
| **Maturity Date** | Date | The date the final payment is due and the contract ends. |
| **Credit Type** | Enum | The category: `LOMBARD`, `MORTGAGE`, `FIXED_TERM`, `OVERDRAFT`. |

### 2. Interest Rate & Calculation

These define how the "cost of borrowing" is computed.

- **Interest Rate**: The annual percentage rate (e.g., 0.05 for 5%).
- **Rate Type**
  - FIXED: Stays the same for the life of the loan.
  - FLOATING: Moves based on a benchmark.
- **Benchmark Index**: Required for floating rates (e.g., SOFR, SARON, EURIBOR). 
- **Spread/Margin**: The amount added to the benchmark (e.g., SARON + 1.5%).
- **Day Count Convention**: The math rule for daily interest (e.g., 30/360, ACT/360).
- **Payment Frequency**: How often the borrower pays (e.g., MONTHLY, QUARTERLY).

### 3. Repayment & Amortization

This defines how the principal is paid back over time.

- **Repayment Type**:
  - BULLET: The entire principal is paid at the very end.
  - AMORTIZING: Regular payments of both principal and interest.
  - INTEREST_ONLY: Only interest is paid; principal remains until maturity.
- **Amortization Schedule**: A table or rule defining the breakdown of each payment.

### 4. Risk & Collateral (The "Safety")

Crucial for wealth management systems to ensure the loan is covered by assets.

- **Collateral ID**: Reference to the assets backing the loan (e.g., a specific Portfolio_ID or Property_ID).
- **Loan-to-Value (LTV)**: The current ratio of the loan balance to the collateral value.
- **Margin Call Threshold**: The LTV percentage that triggers a demand for more collateral.
- **Liquidation Level**: The LTV percentage where the bank automatically sells assets to repay the loan.

### 5. Technical Metadata (API/System Level)

Attributes used for accounting and system processing.

- **Accrued Interest**: The interest earned by the bank but not yet paid by the client.
- **Capitalized Interest Flag**: Boolean indicating if unpaid interest is added back to the principal.
- **Is Overdraft**: Boolean indicating if the position is a negative cash balance.

#### Example Data Model (JSON)

```json
{
  "instrument_id": "CR-990-2026",
  "instrument_type": "CREDIT",
  "sub_type": "LOMBARD_LOAN",
  "currency": "USD",
  "principal": 500000.00,
  "interest": {
    "rate_type": "FLOATING",
    "benchmark": "SOFR_3M",
    "margin": 0.0125,
    "day_count": "ACT/360",
    "payment_frequency": "QUARTERLY"
  },
  "repayment": {
    "type": "INTEREST_ONLY",
    "maturity_date": "2030-01-01"
  },
  "risk_metrics": {
    "collateral_portfolio_id": "PT-772",
    "current_ltv": 0.45,
    "margin_call_level": 0.70
  }
}
```