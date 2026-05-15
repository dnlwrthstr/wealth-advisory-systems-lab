# Futures in the Context of Derivatives

Futures are derivative contracts that obligate a buyer to purchase (and a seller to sell) an asset at a predetermined future date and price. Unlike **Options**, where you have the right but not the obligation, a **Future** is a firm **commitment**.

A Future is a standardized contract traded on an exchange. It is used both for hedging (protecting against price changes) and speculation (betting on price direction).

## 1. Common Types of Futures

| Category | Underlyings | Use Case |
| :--- | :--- | :--- |
| **Commodity Futures** | Oil, Gold, Wheat, Corn | Producers locking in selling prices; speculators betting on supply shocks. |
| **Financial Futures** | Stock Indices (S&P 500), Bonds | Hedging against broad market drops or interest rate changes. |
| **Currency Futures** | EUR/USD, JPY/USD | Businesses managing international trade payment risks. |

## 2. Key Concepts: Long vs. Short

| Position | Market Outlook | Objective |
| :--- | :--- | :--- |
| **Long (Buy)** | **Bullish** | You expect the price to rise. You profit if the market price exceeds your contract price. |
| **Short (Sell)** | **Bearish** | You expect the price to fall. You profit if the market price drops below your contract price. |

## 3. Futures Data Attributes

When modeling a Futures instrument for a data schema, these attributes are essential for identifying the contract and calculating margin requirements.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying ID** | String/UUID | The asset the contract tracks (e.g., Crude Oil WTI). |
| **Expiry Date** | Date | The date the contract must be settled. |
| **Contract Size** | Integer | The multiplier (e.g., 1,000 barrels for oil, 100 oz for gold). |
| **Initial Margin** | Decimal | The "down payment" required to open the position. |
| **Tick Size** | Decimal | The minimum price fluctuation allowed on the exchange. |

## 4. Comparison: Futures vs. Options

While both are derivatives, the risk profiles differ significantly.

| Feature | Futures | Options |
| :--- | :--- | :--- |
| **Obligation** | **Mandatory** for both parties. | Optional for the buyer; mandatory for the seller. |
| **Upfront Cost** | Margin (refundable collateral). | Premium (non-refundable fee). |
| **Risk** | Theoretically unlimited for both. | Limited to premium for the buyer. |
| **Time Decay** | Not a primary factor. | Critical (measured by **Theta**). |

## 5. Technical Data Model (JSON Example)

```json
{
  "instrument_id": "FUT-CL-MAR26",
  "name": "Crude Oil WTI March 2026",
  "type": "DERIVATIVE",
  "sub_type": "FUTURE",
  "identifiers": {
    "ticker": "CLH26",
    "exchange_mic": "XNYM"
  },
  "specifications": {
    "underlying": "WTI_CRUDE_OIL",
    "contract_unit": "BARRELS",
    "contract_size": 1000,
    "currency": "USD"
  },
  "dates": {
    "effective_date": "2026-02-13",
    "maturity_date": "2026-03-20"
  }
}
```

## Futures as a Financial Instrument / Security

To model a Future in a financial system, it must be defined by its contractual obligations, margin requirements, and standardized identifiers.

### 1. Mandatory Technical Identifiers

Because Futures are traded on regulated exchanges (like the CME or EUREX), they require specific metadata for clearing and settlement:

- **Ticker Symbol**: The exchange-specific code (e.g., CL for Crude Oil, ES for S&P 500 E-mini).

- **Expiry Code**: A combination of the month and year (e.g., H6 for March 2026).

- **ISIN**: While many use tickers, most standardized futures are assigned an ISIN for global tracking.

### 2. Futures Data Attributes

If you are building a data model for a Futures contract, these are the essential fields:

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Underlying ID** | String/UUID | The asset the contract tracks (e.g., Crude Oil WTI). |
| **Expiry Date** | Date | The date the contract must be settled. |
| **Contract Size** | Integer | The multiplier (e.g., 1,000 barrels for oil, 100 oz for gold). |
| **Initial Margin** | Decimal | The "down payment" required to open the position. |
| **Tick Size** | Decimal | The minimum price fluctuation allowed on the exchange. |

### 3. Margin & Risk Management

Unlike Equity Securities, where you pay the full price upfront, Futures utilize leverage.

- **Initial Margin**: The minimum collateral required to open the instrument position.
- **Maintenance Margin**: The minimum balance required to keep the position open.
- **Mark-to-Market (MtM)**: The daily process where profits and losses are calculated and settled in the cash account.

### 4. Comparison: Futures vs. Forward Contracts

While similar in concept, their structure as an instrument differs significantly:

| Feature | Future (Security/Instrument) | Forward (Private Contract) |
| :--- | :--- | :--- |
| **Trading Venue** | Regulated Exchange | Over-the-Counter (OTC) |
| **Standardization** | Highly Standardized | Custom/Bespoke |
| **Liquidity** | High (Easy to exit) | Low (Difficult to cancel) |
| **Counterparty Risk** | Minimal (Clearing House) | High (Direct relationship) |

### 5. Technical Data Model (JSON Example)

This structure represents a Future in a modern trading API:

```json
{
  "instrument_id": "FUT-GOLD-APR26",
  "type": "DERIVATIVE",
  "sub_type": "FUTURE",
  "identifiers": {
    "ticker": "GCJ6",
    "exchange": "COMEX"
  },
  "specifications": {
    "underlying": "GOLD",
    "contract_size": 100,
    "unit": "TROY_OUNCES",
    "tick_size": 0.10
  },
  "settlement": {
    "method": "PHYSICAL",
    "currency": "USD",
    "maturity_date": "2026-04-28"
  }
}
```

