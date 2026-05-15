# Commodity Index

To distinguish between a **Single Commodity** and a **Commodity Index**, the CFI system shifts the focus from the physical "stuff" to a "mathematical basket."

a Single Commodity (like Gold) represents a specific physical asset, whereas an Index represents a diversified performance metric.

## 1. Single Commodity (e.g., Gold Future)

When you are modeling a single asset, the 3rd character of the CFI code specifies exactly what it is.

- **CFI Code: F T M S X C**
- **F**: Future (Category)
- **T**: Commodity (Group)
- **M**: **Metals** (The specific sub-group)
- **S**: Standardized
- **X**: (Attribute not applicable)
- **C**: Cash Settlement

## 2. Commodity Index (e.g., Bloomberg Commodity Index)

For an index, the system stops looking at "Metals" or "Energy" and instead classifies the underlying as an **Index**.

- **CFI Code: F T I S X C**
- **F**: Future (Category)
- **T**: Commodity (Group)
- **I**: Index (The 3rd character changes to denote a basket of assets)
- **S**: Standardized
- **X**: (Attribute not applicable)
- **C**: Cash Settlement

### Key Differences for the Data Model

| Feature | Single Commodity | Commodity Index |
| :--- | :--- | :--- |
| **Asset Identifier** | Linked to a specific "Underlying" (Gold, Oil). | Linked to an "Index Provider" (S&P, Bloomberg). |
| **Pricing Source** | Direct exchange price (e.g., COMEX). | A calculated value based on multiple futures. |
| **PMS Risk Flag** | Concentration Risk (exposed to one market). | Systematic Risk (exposed to the broad economy). |
| **CFI Sub-group** | **M** (Metals), **E** (Energy), etc. | **I** (Index). |

### Why this matters for the PMS "Engine"

An index-based instrument requires the system to handle **Rebalancing**. Because the Bloomberg Commodity Index changes the "weight" of its components (e.g., 30% Gold, 20% Oil) once a year, the PMS needs to be aware that the "Index" it is tracking is actually a dynamic target.

> **Technical Note**: If you are using **ETFs** to trade commodities (like the ticker GLD for gold), the CFI code will actually start with E (Equity) because you own shares in a trust, not the gold itself.

## S&P GSCI (Goldman Sachs Commodity Index)

Getting the **S&P GSCI (Goldman Sachs Commodity Index)** depends on whether you are looking for live data to power a PMS or a **tradable instrument** to put in a portfolio.

Since the index was acquired from Goldman Sachs in 2007, it is now owned and managed by S&P Dow Jones Indices.

### 1. Professional Data Sources (For a PMS)

If you are building or using a Portfolio Management System, you typically get the index values through a "Data License" or a terminal.

- **The Source: S&P Dow Jones Indices** (via their **SPICE** platform). They are the official publishers.
- **Terminals: Bloomberg** (Ticker: SPGSCI for the spot index or SPGSCITR for total return) and **Refinitiv/Reuters** (RIC: SPGSCI).
- **Direct Feeds**: Large institutions often get this data via API or SFTP from providers like **ICE Data Services** or **S&P Global**.

### 2. Tradable Instruments (For Investors)

You cannot "buy" the index directly because it is just a number. Instead, you buy products that track it:

- **ETFs**: The most common way for retail and institutional investors. The iShares S&P GSCI Commodity-Indexed Trust (Ticker: GSG) is the primary ETF designed to track the GSCI.
- **Futures**: If you want direct exposure without an ETF wrapper, the CME Group (Chicago Mercantile Exchange) offers S&P GSCI Futures (Ticker: GD).
- **Swaps**: For institutional portfolios, banks offer **Total Return Swaps (TRS)** on the GSCI, which allows you to receive the index performance in exchange for a floating interest rate (like SOFR).

### 3. Free/Retail Information

If you just need to check the price or historical performance:

- **S&P Global Website**: They provide a public page for the S&P GSCI with daily performance and methodology.
- **Financial Sites**: Sites like **Investing.com**, **Trading Economics**, or **MacroMicro** offer charts and historical daily closing prices.

#### Which version do you need?

When you go to pull the data, you will see three versions. It is vital to pick the right one for your PMS:

1. **Spot Index**: Tracks the current price of the underlying commodities. (Rarely used for portfolios).
2. **Excess Return (ER)**: Tracks the price of the futures plus the "roll yield" (the cost/benefit of moving to new contracts).
3. **Total Return (TR)**: Tracks the Excess Return plus the interest earned on the cash collateral (usually T-Bills). **This is the standard for benchmarking a portfolio.**

## Commodity Index in a PMS

Modeling a **Commodity Index** (like the S&P GSCI or BCOM) is significantly different from modeling an Equity index (like the S&P 500) because of one fundamental reality: **Commodities don't have "spot" prices** you can easily buy. To model a commodity index in a Portfolio Management System (PMS), you aren't just tracking a basket of prices; you are modeling a **rolling schedule of derivative contracts**.

### 1. The Core Difference: "Rolling" vs. "Holding"

- **Equity Index**: You model this as a "Buy and Hold" basket. If Apple is 7% of the index, you buy Apple shares and sit on them.
- **Commodity Index**: You cannot easily store 10,000 barrels of oil. Therefore, the index is modeled as a **synthetic position** made of **Futures Contracts**. Because futures expire, the model must include a **Roll Methodology**.

### 2. The Three Layers of the Model

To digitize a commodity index, your system needs to track three distinct components:

#### A. The Weighting Schema (The Basket)

Unlike equity indexes which are usually Market Cap weighted, commodity indexes are often:

- **Production Weighted**: (e.g., GSCI) Heavily skewed toward Energy because the world produces more Oil than Cocoa.
- **Liquidity Weighted**: (e.g., BCOM) Balanced based on how much trading volume each commodity has.
- **Capping Rules**: Limits to ensure one sector (like Energy) doesn't take over 50% of the model.

#### B. The Roll Schedule (The Engine)

This is the most complex part of the model. You must program the system to know:

- **The Roll Window**: On which days of the month does the index move from the "Front Month" contract to the "Next Month"? (e.g., the 5th through 9th business day).
- **The Contract Table**: Which specific months are traded? (Some commodities only trade in March/June/Sept/Dec).

#### C. The Yield Components

A commodity index model calculates returns using three pieces of data:

1. **Price Return**: The change in the price of the futures.
2. **Roll Yield**: The profit or loss generated by selling an expiring contract and buying the next one (influenced by **Contango** or **Backwardation**).
3. **Collateral Yield**: The interest earned on the cash held to back the futures (usually T-Bill rates).

### 3. Comparison: Commodity vs. Equity Index Models

| Feature | Equity Index Model | Commodity Index Model |
| :--- | :--- | :--- |
| **Underlying Asset** | Shares of Stock | Futures Contracts |
| **Maintenance** | Rebalancing (Quarterly) | **Rolling (Monthly)** |
| **Income Source** | Dividends | Collateral Interest + Roll Yield |
| **Corporate Actions** | Splits, Mergers | **Contract Expirations** |
| **Pricing** | Last Traded Price | Settlement Price of specific expiries |

### 4. How to Model it in your System

If you are setting up this index in a database, your **CFI code** would be **F T I S X C**. However, your data schema needs these specific fields:

1. **Index Multiplier**: The value used to convert the index points into currency.
2. **Base Date/Value**: The starting point (e.g., Jan 2, 1970 = 100).
3. **Component Map**: A list of the underlying commodities and their "Percentage of Index Value" (PIV).
    > **The "Gotcha"**: In an equity index, $1 + 1 = 2$. In a commodity index, the price of the commodities can go up, but you can still **lose money** if the "Roll Yield" is negative (Contango). Your model must account for this "decay."


