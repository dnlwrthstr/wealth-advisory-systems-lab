# Portfolio Raw Data 

To build a robust investment portfolio from a Core Banking System (CBS), the raw data must bridge the gap between simple accounting and complex financial analysis.

Building this requires three distinct data pillars: **Master Data** (the "What"), **Position/Transaction Data** (the "How much"), and **Market Data** (the "Value").

## 1. Raw Data Requirements from the CBS

The following table outlines the granular data points typically fetched to establish the baseline of a portfolio.

| Data Category | Key Data Attributes (Raw Fields) | Purpose |
| :--- | :--- | :--- |
| **Client Master** | Client ID, Tax Residency, Risk Profile (MiFID/Suitability), Account Currency | Determining tax treatment and regulatory eligibility. |
| **Position Data** | ISIN/Ticker, Quantity (Long/Short), Book Value, Settle Date, Custodian ID | The "snapshot" of what is currently held in the vault. |
| **Transaction Data** | Trade Date, Transaction Type (Buy/Sell/Corporate Action), Fees, Accrued Interest | Reconstructing performance and historical cost basis. |
| **Cash Data** | Account Balance, Blocked Funds, Currency, Overdraft Limits | Assessing liquidity and "dry powder" for new investments. |
| **Instrument Static** | Asset Class, Maturity Date, Coupon Rate, Seniority, Issuer Country | Categorizing the risk and type of asset. |

## 2. Asset Class & Valuation Logic

Raw CBS data is often just numbers; you must apply specific logic to "valuate" these positions correctly.

### Common Valuation Models

- **Fixed Income (Bonds)**:

$$
Price_{Clean} + Accrued\ Interest = Price_{Dirty}
$$

*Logic*: The CBS provides the coupon rate and last payment date. Your system calculates the daily "accrual" to show the true market value.

- **Equities**:

$$
Quantity \times Market\ Price_{Last}
$$

*Logic*: Usually straightforward, but requires logic for **Adjusted Prices** (accounting for stock splits or dividends).

- **FX & Derivatives**:

$$
Notional \times (Spot\ Rate - Strike)
$$

*Logic*: Requires real-time exchange rates to convert non-base currency holdings into the "Reporting Currency."

## 3. Regulatory & Compliance Logic

Once the portfolio is built, it must be "checked" against legal frameworks (like MiFID II, Basel III, or local central bank rules).

- **Diversification Checks**: Logic to ensure no single issuer exceeds a certain percentage (e.g., the "5/10/40" rule for UCITS funds).
- **Concentration Risk**: Aggregating positions across different accounts to see if the bank is overly exposed to one sector (e.g., Real Estate).
- **Suitability & Appropriateness**: Comparing the Instrument Risk Rating (from the CBS) against the Client Risk Profile.
  - *Example*: If a "Conservative" client holds a "High Risk" Crypto ETP, the system must trigger a regulatory breach flag.
- **AML/KYC Thresholds**: Monitoring large inflows or outflows that deviate from the client's stated "Source of Wealth."

## 4. The Data Flow Architecture

1. **Extraction**: CBS pushes raw XML/JSON or Flat Files via API or Batch.
2. **Enrichment**: Your system joins CBS data with **Market Data Providers** (Bloomberg, Reuters) for prices and ratings.
3. **Transformation**: Calculating Net Asset Value (NAV) and Performance (TWR/MWR).
4. **Reporting**: Generating Regulatory Returns (e.g., COREP/FINREP) and Client Statements.

## 5. Sample Position Data (JSON)

```json
{
  "positionId": "POS-9928371-CH",
  "accountReference": "ACC-550011",
  "instrumentStatic": {
    "isin": "US0378331005",
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "assetClass": "Equity",
    "subClass": "Common Stock",
    "currency": "USD",
    "multiplier": 1,
    "isLiquid": true
  },
  "holdingDetails": {
    "quantity": 150.00,
    "blockedQuantity": 0.00,
    "averagePurchasePrice": 172.45,
    "totalCostBasis": 25867.50,
    "lastTradeDate": "2023-10-15T14:30:00Z",
    "settlementStatus": "Settled"
  },
  "valuation": {
    "marketPrice": 189.20,
    "priceSource": "REUTERS",
    "priceDate": "2023-10-26T21:00:00Z",
    "marketValueBase": 28380.00,
    "unrealizedPL": 2512.50,
    "accruedInterest": 0.00
  },
  "complianceFlags": {
    "mifidEligible": true,
    "complexInstrument": false,
    "sanctionCheckStatus": "Passed"
  }
}
```

### Key Logic Applied to this Data

When this raw data hits your portfolio engine, the following logic is usually triggered immediately:

- **Forex Translation**: If the *instrumentStatic.currency* (USD) differs from the *accountReference* base currency (e.g., EUR), the system fetches the current $EUR/USD$ spot rate to normalize the *marketValueBase*.
- **Corporate Action Adjustment**: The logic checks if the *averagePurchasePrice* needs to be adjusted for historical splits or spin-offs to ensure the *unrealizedPL* is accurate.
- **Regulatory "Hard" Limits**: The system maps the *assetClass* and *isin* against the client's risk profile. If *complexInstrument* is *true* but the client is "Retail/Non-Sophisticated," a compliance alert is generated.**
- **Wash Sale Detection**: The *lastTradeDate* is compared against previous sell orders of the same ISIN to determine tax loss harvesting eligibility (primarily for US-based reporting).
