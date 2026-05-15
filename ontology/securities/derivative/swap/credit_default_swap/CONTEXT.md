# Credit Default Swap (CDS) in the Context of Derivatives

A ***Credit Default Swap (CDS)*** is a financial derivative that acts like an insurance policy against the risk of a "Credit Event" (default) by a specific borrower—usually a corporation or a sovereign government. It allows an investor to "swap" their credit risk with another party.

In a CDS, the **Buyer** makes periodic payments (the "Spread") to the **Seller**. In return, the **Seller** agrees to pay the **Buyer** a set amount if the underlying borrower defaults on its debt.

## Core Mechanics: The Insurance Analogy

| Role | Action | Analogy |
| :--- | :--- | :--- |
| **Protection Buyer** | Pays a periodic premium (Spread). | The Policyholder. |
| **Protection Seller** | Receives the premium; assumes the risk. | The Insurance Company. |
| **Reference Entity** | The company or government being "insured." | The Insured Asset (e.g., a house). |

## Why Use a Credit Default Swap?

1. **Hedging**: A bondholder who is worried that a company might go bankrupt buys a CDS to protect their investment.
2. **Speculation**: An investor who doesn't own the bond but believes a company is likely to default can buy a CDS to profit from that event. This is often called a "Naked CDS."
3. **Arbitrage**: Professional traders use CDS spreads to look for price discrepancies between a company's stock and its debt.

## Key Instrument Attributes for Modeling a CDS

To model a CDS as a financial instrument, you need to capture the following technical data points:

### 1. The Reference Obligation

- **Reference Entity**: The legal entity whose credit risk is being traded (e.g., "Ford Motor Co" or "Republic of Italy").
- **Seniority**: The rank of the debt being insured (e.g., SENIOR_UNSECURED or SUBORDINATED). This changes the payout in a default.

### 2. The Economics (The "Spread")

- **CDS Spread (Premium)**: Expressed in Basis Points (bps) per year.
  - *Example*: A spread of 100 bps means the buyer pays 1% of the notional amount annually. 
- **Notional Amount**: The face value of the debt being protected (e.g., $10,000,000).
- **Payment Frequency**: Usually quarterly.

### 3. The "Credit Event" (The Trigger)

The contract must define what constitutes a default. Standard triggers include:

- **Failure to Pay**: Missing an interest or principal payment.
- **Bankruptcy**: Legal filing for insolvency.
- **Restructuring**: Changing the terms of the debt to the detriment of the lender.

## Settlement Methods

If a credit event occurs, the contract is settled in one of two ways:

- **Physical Settlement**: The Buyer delivers the defaulted bond to the Seller, and the Seller pays the Buyer the full Face Value (100%) in cash.
- **Cash Settlement**: The Seller pays the Buyer the difference between the Face Value and the current market price of the "broken" bond (Recovery Value).

## Risks of CDS Positions

#### Counterparty Risk

This is the most significant risk. If the Reference Entity defaults, but the Protection Seller (e.g., a bank) also goes bankrupt at the same time, the Buyer receives nothing. This was a major factor in the 2008 financial crisis.

#### Jump-to-Default Risk

The value of a CDS can stay stable for years and then suddenly skyrocket if a company collapses overnight, leading to extreme volatility.

### Technical Data Model (JSON Example)

```json
{
  "instrument_id": "CDS-FORD-5Y-SNR",
  "type": "DERIVATIVE",
  "sub_type": "CREDIT_DEFAULT_SWAP",
  "reference_entity": "Ford Motor Credit Co LLC",
  "seniority": "SENIOR_UNSECURED",
  "notional_amount": 1000000.00,
  "currency": "USD",
  "cds_spread_bps": 125.0,
  "effective_date": "2026-02-12",
  "maturity_date": "2031-02-12",
  "payment_frequency": "QUARTERLY",
  "settlement_method": "CASH"
}
```

## Credit Default Swap (CDS) as a security

To model a Credit Default Swap (CDS) as a security/instrument in a financial system, you must capture data that defines the "insurance" contract, the entities involved, and the ongoing valuation (the "Spread").

Unlike a standard bond, a CDS is a bilateral contract, so the data must represent both the underlying risk and the payment obligations.

### 1. Reference Entity Data

This is the most critical data set. It defines who the protection is being bought against.

- **Reference Entity Name**: The legal name of the issuer (e.g., Volkswagen AG)
- **Reference Entity Identifier**: Typically a LEI (Legal Entity Identifier) or RED Code (Reference Entity Database code, the industry standard).
- **Seniority**: The "tier" of the debt being insured. This is vital because subordinated debt defaults more often than senior debt.
  - *Values*: SNR (Senior), SUB (Subordinated), JRSUB (Junior Subordinated).
- **Reference Obligation**: The specific ISIN of a bond used as the "benchmark" for the credit event.

### 2. Contractual & Economic Terms

These define the "Notional" (the size of the bet) and the timeline.

### CDS Data Attributes

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Notional Amount** | Decimal | The face value of protection (e.g., 5,000,000). |
| **Currency** | String | The ISO currency of the contract (usually USD or EUR). |
| **Effective Date** | Date | When the protection starts. |
| **Maturity Date** | Date | When the contract expires (Standard terms are 1, 3, 5, 7, or 10 years). |
| **Business Day Conv.** | Enum | How to handle weekends (e.g., `FOLLOWING`, `MODIFIED_FOLLOWING`). |

### . The Coupon (The Spread)

This represents the "Premium" paid for the insurance.

- **Fixed Rate (Coupon)**: Standardized CDS contracts usually pay a fixed coupon of 100 bps (for investment grade) or 500 bps (for high yield).
- **Upfront Payment**: Because the market "Spread" changes daily but the "Coupon" is fixed, an upfront payment is often made at the start of the trade to equalize the value.
- **Payment Frequency**: Almost always QUARTERLY
- **Day Count Convention**: Usually ACT/360.

### 4. Credit Event Definitions

This data tells the system what triggers a payout.

- **Restructuring Type**: Defines if a debt restructuring counts as a default.
  - Values: NR (No Restructuring), CR (Old Restructuring), MR (Modified Restructuring), MMR (Modified-Modified).
- **Credit Event Triggers**: A list of booleans:
  - failureToPay: True/False 
  - bankruptcy: True/False
  - acceleration: True/False

### 5. Valuation & Risk (The "Greeks")

For portfolio management, you need the "Mark-to-Market" data.

- **Market Spread**: The current price in the market to buy protection.
- **DV01 (Risky PV01)**: How much the value of the CDS changes if the spread moves by 1 basis point.
- **Recovery Rate**: The assumed value of the bond after default (Standard is 40% for Senior Debt).
- **Implied Probability of Default (PD)**: A calculated value showing how likely the market thinks a default is.

### Technical Data Model Example (JSON)

```json
{
  "instrument_id": "CDS_DAIMLER_5Y_SNR",
  "type": "DERIVATIVE",
  "sub_type": "CREDIT_DEFAULT_SWAP",
  "reference_data": {
    "entity_name": "Mercedes-Benz Group AG",
    "red_code": "7G89A2",
    "seniority": "SENIOR_UNSECURED"
  },
  "economics": {
    "notional": 10000000.00,
    "currency": "EUR",
    "fixed_coupon": 0.0100,
    "maturity_date": "2031-06-20"
  },
  "valuation": {
    "market_spread_bps": 85.2,
    "recovery_rate": 0.40,
    "accrued_premium": 1250.00
  }
}
```
