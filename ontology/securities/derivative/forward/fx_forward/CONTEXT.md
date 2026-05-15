# FX Forwards as a Financial Instrument

Unlike Futures, which are standardized and exchange-traded, FX Forwards are private, over-the-counter (OTC) agreements to exchange one currency for another at a fixed rate on a future date.

An FX Forward is a primary tool for hedging currency risk. It is a firm obligation between two parties (usually a client and a bank) to trade a specific amount of "Base" currency for a "Quote" currency.

## 1. Mandatory Technical Identifiers

Because these are OTC instruments, they often lack a standard ISIN, relying instead on internal system IDs and trade confirmation numbers:

- **Currency Pair**: The two currencies involved (e.g., EUR/USD).
- **Counterparty ID**: The **Legal Entity Identifier (LEI)** of the bank or institution on the other side of the trade.
- **Value Date**: The specific date when the actual exchange of funds occurs.

## 2. FX Forward Data Attributes

In a financial data model, an FX Forward requires the following fields to track exposure and settlement:

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Near Amount** | Decimal | The amount of the first currency to be exchanged. |
| **Near Currency** | String | The ISO 4217 code for the base currency (e.g., `USD`). |
| **Forward Rate** | Decimal | The agreed-upon exchange rate for the future date. |
| **Value Date** | Date | The date of the final payment/exchange (Maturity). |
| **Credit Support** | Enum | Links to collateral or margin requirements (e.g., `CSA_AGREEMENT`). |

## 3. Comparison: FX Forward vs. FX Spot

| Feature | FX Spot | FX Forward |
| :--- | :--- | :--- |
| **Settlement Date** | Typically T+2 (2 business days). | Any date beyond T+2. |
| **Rate Basis** | Current Market Price (Spot Rate). | Spot Rate ± Forward Points (Interest diff). |
| **Purpose** | Immediate Liquidity/Exchange. | Hedging future cash flows/Risk Mgmt. |

## 4. The Concept of "Mark-to-Market" (MtM)

While a loan has a stable principal, the value of an FX Forward fluctuates based on the current market exchange rate versus your locked-in rate:

- **Unrealized Gain**: If the market rate is better than your forward rate, the instrument has positive value (an asset).
- **Unrealized Loss**: If the market rate is worse, the instrument has negative value (a liability).
- **Counterparty Risk**: Unlike Futures (settled via clearing houses), Forwards carry the risk that the other party might default.

## 5. Technical Data Model (JSON Example)

This structure represents an FX Forward for integration into a portfolio management system:

```json
{
  "instrument_id": "FXFWD-EURUSD-20260930",
  "type": "DERIVATIVE",
  "sub_type": "FX_FORWARD",
  "counterparty": {
    "lei": "54930084UKR0MPOU8F65",
    "name": "Global Investment Bank"
  },
  "legs": [
    {
      "direction": "BUY",
      "amount": 1000000.00,
      "currency": "EUR"
    },
    {
      "direction": "SELL",
      "amount": 1085000.00,
      "currency": "USD"
    }
  ],
  "terms": {
    "forward_rate": 1.0850,
    "value_date": "2026-09-30",
    "is_deliverable": true
  }
}
```


