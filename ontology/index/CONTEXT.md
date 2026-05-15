# Index - is not a financial instrument!

An index itself (like the SPI or S&P 500) is **not** a financial instrument.

In professional financial data modeling, an index is a Statistical Construct or a Reference Data Point. It is a mathematical formula that tracks the performance of a group of assets, but you cannot "buy" the index itself.

However, there are many **Financial Instruments** that use an index as their Underlying Asset.

## 1. The Distinction in your Notebook

When creating your INSTRUMENT_INDEX.md, you should categorize these separately:

| Category | Definition | Example |
| :--- | :--- | :--- |
| **Reference Index** | A benchmark used to measure value or calculate payments. | **SPI** (Swiss Performance Index), **SOFR**, **LIBOR**. |
| **Financial Instrument** | A tradable contract that derives value from the index. | **SPI Future**, **SPI ETF**, **SPI Option**. |


## 2. How Professional Clients Trade the SPI

Institutional clients use the following instruments to gain exposure to the SPI index:

- **Index Futures (CFI: FF\*\*\*\*)**: A mandatory contract to buy or sell the value of the SPI at a future date.
- **Index Options (CFI: OC\*\*\*\*)**: The right, but not the obligation, to trade based on the SPI level.
- **Exchange-Traded Funds (ETFs)**: A security that holds the actual stocks within the SPI to mimic its performance.
- **Total Return Swaps (TRS) (CFI: SBT\*\*\*)**: A private contract where one party pays the "Total Return" of the SPI index to another party in exchange for a funding rate.

### Examples:

- **SPI ETF (CFI: IE00B3\*\*\*\*)**: An exchange-traded fund that tracks the SPI index.
- **SPI Option (CFI: IE00B3\*\*\*\*)**: A derivative contract that gives the holder the right to buy or sell the SPI at a predetermined price.
- **SPI Swap (CFI: ISIN: CH0000\*\*\*\*)**: A contract that exchanges the SPI index performance for a fixed rate of return.
- **SPI Forward (CFI: ISIN: CH0000\*\*\*\*)**: A contract to buy or sell the SPI at a future date at a predetermined price.
- **SPI Swap (CFI: ISIN: CH0000\*\*\*\*)**: A contract that exchanges the SPI index performance for a fixed rate of return.
- **SPI Forward (CFI: ISIN: CH0000\*\*\*\*)**: A contract to buy or sell the SPI at a future date at a predetermined price.
- **SPI Swap (CFI: ISIN: CH0000\*\*\*\*)**: A contract that exchanges the SPI index performance for a fixed rate of return.
- **SPI Forward (CFI: ISIN: CH0000\*\*\*\*)**: A contract to buy or sell the SPI at a future date at a predetermined price.
- **Total Return Swaps (TRS) (CFI: SBT\*\*\*)**: A private contract where one party pays the "Total Return" of the SPI index to another party in exchange for a funding rate.

## 3. Data Model for an Index (Reference Data)

> The data model for an Index: An Index is not a financial instrument.!!

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Index Name** | String | The official name (e.g., Swiss Performance Index). |
| **Ticker/Symbol** | String | The market identifier (e.g., `SPI`). |
| **Administrator** | String | The entity that calculates the index (e.g., SIX Swiss Exchange). |
| **Calculation Type** | Enum | `PRICE_RETURN` (price only) or `TOTAL_RETURN` (includes dividends). |
| **Constituent Count** | Integer | Number of assets within the index. |f you were to create an INDEX_REFERENCE.md, the attributes would look different from your instrument files because there is no "Notional" or "Counterparty" for a benchmark.

## 4. Why the distinction matters for Institutional Clients

For a professional client, the SPI is "Reference Data." If they trade an SPI Future, their system needs to link:

1. The **Instrument Data** (Expiry, Tick Size, Margin).
2. The Market Data (The current level of the SPI index provided by a data vendor like Bloomberg or Reuters).

An index is the ruler; the financial instrument is the contract that bets on what the ruler will show.
