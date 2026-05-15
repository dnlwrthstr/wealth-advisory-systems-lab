# Equity in the context of Securities

When you buy an equity (commonly known as a stock or share), you aren't just lending money—you are buying a piece of ownership in a company. Unlike a bondholder, who is a creditor, an equity holder is a part-owner. If the company prospers, you share in the profits; if it fails, you are last in line to get paid.

## Common Types of Equity

| Type | Description | Risk/Reward Profile |
| :--- | :--- | :--- |
| **Common Stock** | Standard ownership. Includes voting rights and potential dividends. | Higher risk, but highest potential for long-term growth. |
| **Preferred Stock** | A hybrid between a bond and a stock. Pays fixed dividends and has priority over common stock. | Lower volatility than common stock; usually no voting rights. |
| **Growth Stocks** | Companies expected to grow at a rate above the market average (e.g., Tech). | High potential for capital gains; rarely pay dividends. |
| **Value Stocks** | Established companies trading for less than their "intrinsic" worth. | Often pay steady dividends; seen as "bargains." |

## How Equity Works

To understand equity, you need to grasp these core concepts:

- **Share Price**: The current market cost to buy one "unit" of ownership. This fluctuates throughout the trading day based on supply and demand.

- **Market Capitalization (Market Cap)**: The total value of the company.
  - Calculation: $\text{Share Price} \times \text{Total Number of Shares Outstanding}$

- Dividends: A portion of the company’s profit paid out to shareholders, usually quarterly. Think of this as a "thank you" for owning the stock.

## Why Do People Buy Equities?

Equities are generally riskier than bonds, but they offer the potential for much higher returns through:

- **Capital Appreciation**: The hope that you can sell the stock for more than you paid (buy low, sell high).

- **Dividend Income**: A way to generate passive cash flow from profitable companies.

- **Voting Rights**: For large investors, equity provides a seat at the table to influence company decisions (like electing the Board of Directors).

## The Concept of "Residual Claim"

This is the fundamental difference between bonds and equities.

- **Bondholders** have a contractual claim: they must be paid their interest first.

- **Equity holders** have a **residual claim**: they get whatever is left over after all employees, suppliers, tax authorities, and bondholders have been paid.
  
    **The Upside**: If a company becomes the next giant, bondholders still only get their fixed interest, while equity holders' wealth can grow exponentially.

    **The Downside**: If the company goes bankrupt, equity holders are usually wiped out and get \$0.

## Valuation: How is a Stock Priced?

Unlike bonds, which are priced based primarily on interest rates and credit, stocks are priced based on future earnings expectations.

## Key Valuation Metrics

Unlike bonds, which are priced based primarily on interest rates and credit, stocks are priced based on future earnings expectations.

## Key Valuation Metric

| Metric | What it tells you |
| :--- | :--- |
| **P/E Ratio** | Price-to-Earnings: How much investors pay for $1 of the company's profit. |
| **EPS** | Earnings Per Share: The portion of profit allocated to each individual share. |
| **Dividend Yield** | The annual dividend payment divided by the share price (as a %). |

### Understanding the Math
In case you need to perform these calculations within your Jupyter Notebook using Python or just want the reference, here are the standard formulas:
P/E Ratio: 

$$
\text{P/E Ratio} = \frac{\text{Market Value per Share}}{\text{Earnings per Share (EPS)}}
$$

EPS:
$$
\text{EPS} = \frac{\text{Net Income} - \text{Preferred Dividends}}{\text{Weighted Average Shares Outstanding}}

$$

Dividend Yield: 

$$
\text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Price per Share}}
$$

## Risks of Equity Positions

### Market Risk (Systematic Risk)

The risk that the entire stock market drops due to a recession or global event. No matter how good the company is, its stock will likely fall with the market.

### Business Risk

The risk specific to that company—perhaps their new product fails, or a competitor disrupts their industry (e.g., Netflix vs. Blockbuster).

### Volatility Risk

Stock prices can swing wildly in the short term based on news, rumors, or earnings reports. This can lead to "panic selling" if an investor lacks a long-term horizon.

## Equity Issuance: IPOs

When a company needs to raise money to grow, they "go public" via an **Initial Public Offering (IPO)**.

- **Primary Market**: The company creates new shares and sells them to big investors to raise cash for the business.

- **Secondary Market**: This is the Stock Exchange (like the NYSE or NASDAQ). Once the IPO is over, investors trade the shares among themselves. The company does not get money when you buy a stock on the secondary market.

## Key Components of an Equity Position

### The Holding (The "Stake")

- **Ticker Symbol**: The unique code (e.g., AAPL, TSLA, NVDA).

- **Quantity**: How many shares you own.

- **Cost Basis**: What you paid per share, including any transaction fees.

### The Performance (The "Gain/Loss")

- **Unrealized Gain/Loss**: The difference between your cost basis and the current market price.

- **Total Return**: The combination of share price increase + dividends received.

### The Corporate Action

- **Stock Splits**: When a company increases the number of shares to lower the price (e.g., a 2-for-1 split). You own more shares, but the total value remains the same.

- **Buybacks**: When a company buys its own shares back from the market, usually increasing the value of the remaining shares.

## Equity as a Security / Instrument

In financial data models, an **Equity Instrument** is a structured record that identifies a specific ownership claim. Unlike a bank account balance, an equity instrument must be defined by its regulatory identifiers, corporate structure, and the specific rights it confers to the holder.

### 1. Mandatory Technical Identifiers

To ensure a trade or position is tracked correctly across global markets, an equity instrument requires these unique codes:

- **ISIN (International Securities Identification Number)**: The global standard (e.g., US0378331005 for Apple).

- **Ticker / Symbol**: The exchange-specific shortcode (e.g., AAPL on NASDAQ).

- **LEI (Legal Entity Identifier)**: The code for the company that issued the stock.

- **MIC (Market Identifier Code)**: Identifies the exchange where the instrument is primarily traded (e.g., XNAS for NASDAQ).

### 2. Instrument Classifications

Financial systems use these attributes to determine how to tax the asset and how to calculate its risk:

### Equity Data Attributes

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Share Class** | String | Distinguishes between Class A (voting), Class B (non-voting), or Preferred shares. |
| **Par Value** | Decimal | The nominal value stated in the corporate charter (often \$0.01 or \$0.001). |
| **CFI Code** | String | The "Classification of Financial Instruments" code (e.g., `ESXXXX` for Equity Common Shares). |
| **Voting Ratio** | Decimal | The number of votes per share (usually `1.0`). |

### 3. Corporate Attributes (Metadata)

These attributes link the instrument to the physical company and its economic sector:

- **Sector / Industry**: The high-level categorization (e.g., Information Technology).

- **Country of Incorporation**: Where the company is legally registered (affects withholding taxes).

- **Currency of Denomination**: The currency in which the share price is quoted (e.g., USD, CHF).

### 4. Dynamic Data Points (Market Data)

While the ISIN is static, these values are updated in real-time or daily:

- **Last Trade Price**: The most recent price at which a share was bought or sold.

- **Market Cap Category**: (e.g., Large-Cap, Mid-Cap, Small-Cap).

- **Dividend Status**: A flag indicating if the company is currently paying dividends.

### Technical Data Model (JSON Example)

When modeling an Equity instrument for an API, the structure typically looks like this:

```json
{
  "instrument_id": "EQ-AAPL-NASDAQ",
  "name": "Apple Inc.",
  "type": "EQUITY",
  "sub_type": "COMMON_STOCK",
  "identifiers": {
    "isin": "US0378331005",
    "ticker": "AAPL",
    "exchange_mic": "XNAS"
  },
  "classification": {
    "sector": "Information Technology",
    "industry": "Consumer Electronics",
    "asset_class": "EQUITY"
  },
  "operational": {
    "currency": "USD",
    "has_voting_rights": true,
    "dividend_frequency": "QUARTERLY"
  }
}
```

### Comparison: Equity Instrument vs. Bond Instrument

| Feature | Equity Instrument | Bond Instrument |
| :--- | :--- | :--- |
| **Return Source** | Dividends & Price Growth | Interest (Coupons) |
| **Maturity** | None (Perpetual) | Fixed Date |
| **Legal Status** | Owner (Residual Claim) | Creditor (Contractual Claim) |
| **Key Risk** | Business/Market Performance | Interest Rate / Default |
