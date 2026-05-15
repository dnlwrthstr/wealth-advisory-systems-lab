# Derivatives Market Data - Greeks

In the world of derivatives, data flows through a specific hierarchy. Neither the exchange nor the broker typically "invents" the Greeks; rather, they are calculated using mathematical models based on raw market data.

Here is the breakdown of who provides what and how it reaches your system.


## 1. The Price (Premium)
Source: The Exchange (e.g., CBOE, CME, Eurex).
Form: Real-time data feeds (FIX protocol, WebSocket, or JSON APIs).

The price is set by the open market (the highest bid and the lowest ask). It is provided as:

Bid/Ask/Last: The actual tradable prices.

Mark Price: A calculated "fair value" (usually the midpoint of the bid-ask) used by brokers to determine margin requirements and portfolio value.

## 2. The Greeks
Source: Data Vendors or Internal Pricing Engines.
Form: Calculated fields within a data packet.

The Greeks are not "traded"; they are derived. Because they require complex calculus (usually the Black-Scholes Model for European options or the Binomial Model for American options), they are provided in two ways:

Commercial Data Providers: Companies like Bloomberg, Reuters (Refinitiv), or ICE run the math on their own servers and bundle the Greeks alongside the price in their API responses.

In-House Calculation: Many sophisticated trading platforms receive only the Price and Volatility from the exchange and then use an internal library (like QuantLib) to calculate Delta, Gamma, etc., in real-time.

## 3. The Delivery Format
When you consume this data via an API (like the OpenWealth standard or a broker API), it usually arrives in a structured format, often divided into Static and Dynamic segments.

### A. Market Data Snapshots (REST/JSON)
If you query a ticker, you receive a "state of the union" for that option:

```json
{
  "symbol": "AAPL260619C00200000",
  "price_data": {
    "bid": 12.40,
    "ask": 12.60,
    "last": 12.50
  },
  "greeks": {
    "delta": 0.6512,
    "gamma": 0.012,
    "theta": -0.045,
    "vega": 0.18,
    "iv": 0.245
  }
}
```
### B. Streaming Feeds (WebSocket/FIX)

For active trading, you receive a constant stream of binary or compact text messages. Every time the price of the underlying stock moves, the provider's engine recalculates the Greeks and pushes a partial update to your terminal.
### Summary Table: Option Data Sources

| Data Point | Primary Provider | Calculation Method |
| :--- | :--- | :--- |
| **Strike/Expiry** | The Exchange | Static (Contract Specs) |
| **Bid/Ask Price** | The Market Participants | Matching Engine |
| **Implied Volatility (IV)** | Data Vendor / Model | Derived from Price via Iteration |
| **The Greeks** | Data Vendor / Your System | Mathematical Models ($Black-Scholes$) |

### A Note on "The Truth"
It is important to realize that different providers may show slightly different Greeks for the exact same option. This is because they might use different "risk-free interest rates" or different dividend assumptions in their models. While the Price is a hard fact from the exchange, the Greeks are always an estimate based on a model.
