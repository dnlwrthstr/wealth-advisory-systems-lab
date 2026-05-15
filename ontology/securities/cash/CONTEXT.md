# Cash and Cash Equivalents

In the context of wealth management and securities, **Cash** isn't just the physical bills in a vault. It represents the most liquid asset class in a portfolio—capital that is immediately available for withdrawal or investment. While often viewed as a "neutral" position, cash is a strategic component used for liquidity, risk mitigation, and as a placeholder between investment opportunities.

## Common Types of Cash Positions

| Type | Description | Liquidity |
| :--- | :--- | :--- |
| **Current Account** | Standard "checking" account for daily transactions and fees. | Instant |
| **Savings Account** | Interest-bearing accounts, sometimes with withdrawal limits. | High |
| **Money Market Fund** | Low-risk mutual funds that invest in short-term debt (like T-bills). | T+1 or T+0 |
| **Term Deposits (CDs)** | Cash locked away for a fixed period (e.g., 6 months) for higher interest. | Restricted |
| **Fiduciary Deposits** | Placements made by a bank in the name of the client with a third-party bank. | Fixed Term |

## How Cash Works in a Portfolio

Unlike bonds or stocks, cash does not have a "market price" that fluctuates. Its value is defined by its **Nominal Amount** and its **Purchasing Power**.

- **Currency (FX)**: Cash is always denominated in a specific currency (CHF, USD, EUR). Holding cash in a foreign currency introduces **Exchange Rate Risk**.

- **Interest (Yield)**: While usually lower than bonds, cash can earn interest. This is often tied to central bank "overnight" rates.

- **Settlement**: Cash is the "oil" in the machine. When you sell a stock, the proceeds land in your cash position before they can be reinvested.

## Why Hold Cash?

Investors rarely hold 100% cash, but it serves three vital functions:

1. **Liquidity**: Meeting immediate obligations (e.g., paying management fees, taxes, or lifestyle expenses).
2. **Dry Powder**: Having capital ready to deploy immediately when the stock market drops (buying the dip).
3. **Risk Floor**: In a "bear market" where stocks and bonds are both falling, cash stays at its nominal value, acting as a stabilizer.

## Key Components of a Cash Position

### 1. The Balance (The "Core")

In financial schemas (like OpenWealth), the balance is the primary data point.

- **Book Balance**: The total amount of money physically in the account.

- **Available Balance**: The amount you can actually spend (Book Balance minus "blocked" amounts or pending trades).

### 2. Accrued Interest

Just like bonds, cash accounts accumulate interest daily, even if it is only paid out monthly or annually.

- **Credit Interest**: What the bank pays you on your balance.
- **Debit Interest**: What you pay the bank if your account goes into "overdraft" (a negative balance).

### 3. Value Date (The "Reality Check")

In the world of banking, the date you initiate a transfer is not always the date the money starts earning interest.

- **Transaction Date**: When you clicked "send".
- 
- **Value Date**: The date used by the bank for interest calculation. If you deposit money on Friday, the "Value Date" might be Monday.

## Risks of Cash Positions

While "cash is king," it is not risk-free.

### Inflation Risk
This is the "silent killer" of cash. If your savings account pays 1% interest but inflation is 4%, your cash is losing 3% of its purchasing power every year.

### Counterparty Risk (Bank Failure)

If the bank holding your cash goes bankrupt, your money could be at risk.

- **Protection**: Most jurisdictions have deposit insurance (e.g., esisuisse in Switzerland, FDIC in the US) that protects cash up to a certain limit (usually 100,000 in local currency).

### Currency Risk

If you hold USD but live in Switzerland, and the USD weakens against the CHF, your "wealth" in local terms has decreased even though the number of dollars stayed the same.

## Technical Components in Financial APIs

When processing cash data via API (e.g., OpenWealth), you will encounter specific attributes that define the position:

### The "Overdraft" Flag

In many schemas, cash isn't just a positive number.

- **isOverdraft (Boolean)**: If TRUE, the client owes the bank money. The "asset" has technically become a "liability."

### Blocked Amount

Banks often "earmark" cash for specific purposes.

- **Blocked Amount**: Cash that is in the account but cannot be withdrawn (e.g., used as collateral for a Lombard loan or reserved for a pending trade settlement).

### Comparison: Cash vs. Cash Equivalents

| Feature | Cash (Current Account) | Money Market Funds (Equivalent) |
| :--- | :--- | :--- |
| **Structure** | Bank Deposit | Security/Fund Units |
| **Risk** | Bank Credit Risk | Market Risk (minimal) |
| **Interest** | Set by the bank | Market-driven yield |
| **Access** | Instant | Requires a "Sell" order |

## Cash a security / instrument

In the context of wealth management and securities processing, treating Cash as a security (often referred to as a "Cash Instrument" or "Liquid Instrument") requires more than just a balance. To a core banking system or an API, cash is an asset with specific metadata that allows it to be traded, valued, and settled just like a stock or bond.

Here are the specific properties a cash instrument possesses when treated as a security:

### 1. The Denomination (The "Ticker")

While a stock has an ISIN or a Symbol (e.g., AAPL), a cash instrument’s primary identifier is its ISO 4217 Currency Code (e.g., USD, EUR, CHF).

- **Base Currency**: The currency of the portfolio.
- **Local Currency**: The currency of the specific cash instrument.
- **FX Rate**: The "price" of the cash instrument relative to the portfolio’s base currency.

### 2. Valuation Properties

Unlike a stock, where the price fluctuates and the quantity (shares) stays the same, cash is usually the inverse in accounting terms:

- **Unit Price**: Almost always fixed at 1.00 in its local currency.
- **Quantity**: The actual balance (e.g., 50,000 units of USD).
- **Market Value**: Calculated as $Quantity \times Price \times FX \text{ Rate}$.

### 3. Interest and Yield Metadata

A cash instrument carries "DNA" related to how it grows, which mirrors the attributes of a Floating Rate Note (FRN):

- **Reference Rate**: The benchmark the cash follows (e.g., SOFR for USD, SARON for CHF).
- **Spread/Margin**: The basis points added or subtracted from the reference rate by the custodian.
- **Accrual Convention**: The logic used to calculate daily interest (e.g., Act/360, Act/365, or 30/360).
- **Payment Frequency**: When the "coupon" (interest) is capitalized (Monthly, Quarterly, Annually)

### 4. Lifecycle and Status Flags

In a technical schema, a cash instrument needs "state" indicators to tell the system how to handle it:

- **Asset Class Categorization**: Classified as "Cash," "Cash Equivalent," or "Margin Account."
- **IsCollateral (Boolean)**: Whether this cash position is being used to back a loan (Lombard) or a derivative position.
- **IsSweepable (Boolean)**: Indicates if excess cash in this instrument should be automatically moved ("swept") into a higher-yielding Money Market Fund at the end of the day.

### 5. Settlement and Technical Attributes

Since cash is the medium for all other trades, its instrument properties include "delivery" logic:

- **Settlement Cycle**: Usually T+0 (instant), though some Cash Equivalents like Money Market Funds may be T+1.
- **Account Number/IBAN**: The unique "address" where this specific instrument resides.
- **Nostro/Vostro Indicators**: Technical flags identifying if the cash is held internally or at a correspondent bank.


### Comparison: Stock vs. Cash Instrument

| Property | Equity Security (Stock) | Cash Instrument |
| :--- | :--- | :--- |
| **Identifier** | ISIN / CUSIP | ISO Currency Code |
| **Price** | Market Driven (Variable) | Fixed (1.00) |
| **Quantity** | Number of Shares | Total Balance |
| **Income Type** | Dividends | Interest |
| **Risk** | Market / Systematic | Inflation / Counterparty |


```json
{
  "instrumentId": "CASH-USD-001",
  "instrumentType": "CASH_POSITION",
  "status": "ACTIVE",
  "identifiers": {
    "currencyCode": "USD",
    "isin": null, 
    "internalId": "BANK-NY-9920"
  },
  "attributes": {
    "description": "US Dollar Spot Cash",
    "isCollateral": true,
    "isSweepable": false,
    "overdraftAllowed": true,
    "overdraftLimit": 10000.00
  },
  "valuation": {
    "quantity": 125450.75,
    "unitPrice": 1.00,
    "priceCurrency": "USD",
    "fxRateToBase": 0.8821,
    "marketValueBase": 110660.11,
    "valueDate": "2026-02-16"
  },
  "yieldDetails": {
    "interestRateType": "FLOATING",
    "referenceRate": "SOFR",
    "spreadBps": 15,
    "accrualMethod": "ACT/360",
    "lastInterestCapitalizationDate": "2026-01-31",
    "accruedInterest": 142.30
  },
  "settlement": {
    "settlementCycle": "T+0",
    "custodian": "Global Custody Services",
    "accountIBAN": "US1234567890123456"
  }
}
```




