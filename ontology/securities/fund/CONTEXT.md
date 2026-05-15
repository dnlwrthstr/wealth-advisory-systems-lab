# Fund (Investment Fund) in the Context of Securities

An **Investment Fund** is a supply of capital belonging to numerous investors used to collectively purchase securities while each investor retains ownership and control of their own shares. It is the ultimate "diversification in a box," allowing individual investors to own a tiny slice of hundreds or thousands of different assets (stocks, bonds, commodities) through a single instrument.

## Common Types of Funds

### Comparison of Investment Fund Types

| Type | Structure | Trading Style |
| :--- | :--- | :--- |
| **Mutual Fund** | Open-ended pool. | Bought/Sold at the end of the day via the fund manager. |
| **ETF (Exchange Traded Fund)** | Traded on an exchange like a stock. | Bought/Sold throughout the day at market prices. |
| **Hedge Fund** | Private partnership for high-net-worth individuals. | Often involves complex strategies (shorting, leverage). |
| **Money Market Fund** | Invests in short-term debt (cash equivalents). | Low risk, used for liquidity and capital preservation. |


## How a Fund Works

When you buy into a fund, you aren't buying the underlying assets directly. Instead, you are buying **units** or **shares** of the fund entity itself.

- **Net Asset Value (NAV)**: This is the "price" of a fund share. It is calculated by taking the total value of all assets in the fund, subtracting liabilities, and dividing by the number of shares outstanding.
- **The Portfolio Manager**: The professional or algorithm responsible for deciding which securities to buy and sell within the fund.
- **The Prospectus**: The legal "rulebook" of the fund that defines its goals, risks, and fees.

## Why Invest in Funds?

1. **Instant Diversification**: A single $100 investment in an S&P 500 fund gives you exposure to the 500 largest companies in the US.
2. **Professional Management**: You delegate the research and trading to experts.
3. **Cost Efficiency**: Funds benefit from economies of scale, paying lower transaction fees than an individual investor would.

## Key Values for Modeling a Fund Instrument

To model a fund in a database or API (like OpenWealth), you need to capture the following attributes:

### 1. Identity & Classification

- **ISIN/Ticker**: The unique identifier for the fund.
- **Fund Family**: The company managing the fund (e.g., Vanguard, BlackRock, UBS).
- **Asset Class Focus**: What the fund invests in (Equity, Fixed Income, Real Estate, Multi-Asset).
- **Geographic Focus**: Where it invests (Global, Emerging Markets, US, Europe).

### 2. Operational Attributes

- **NAV (Net Asset Value)**: The current value per share.
- **Total AUM (Assets Under Management)**: The total size of the fund.
- **Dividend Policy**:
  - **Distributing**: Pays out dividends/interest to investors as cash.
  - **Accumulating**: Reinvests dividends back into the fund to increase the share price.
- **Legal Structure**: (e.g., UCITS, SICAV, 40-Act).

### 3. Currency & Hedging

Investors often face Foreign Exchange (FX) risk when a fund invests in international assets. To manage this, funds often offer specific "Hedged" share classes.

- **isCurrencyHedged**: A boolean flag indicating if the fund share class uses derivatives (like FX Forwards) to offset the impact of currency fluctuations.
- **Hedging Currency**: The target currency of the hedge (e.g., a "USD-Hedged" class of a European stock fund).

### 4. Fee Structure (The "Drag")

- **TER (Total Expense Ratio)**: The annual percentage fee charged to cover management and operating costs.
- **Management Fee**: The specific fee paid to the portfolio manager.
- **Performance Fee**: A "bonus" paid to the manager if the fund exceeds a certain benchmark (common in Hedge Funds).

## Risks of Fund Positions

### Market Risk

If the entire stock market drops, the fund will drop with it, regardless of how well the manager picks individual stocks.

### Concentration Risk

Even though a fund is "diversified," it might be heavily weighted in one sector (like Tech). If that sector crashes, the fund suffers disproportionately.

### Tracking Error (For ETFs/Index Funds)

The risk that the fund does not perfectly mimic the performance of the index it is supposed to follow.

## Data Model Example

```joson
{
  "instrument_id": "IE00B4L5Y983",
  "instrument_name": "iShares Core MSCI World UCITS ETF",
  "type": "FUND",
  "sub_type": "ETF",
  "issuer": "BlackRock",
  "currency": "USD",
  "nav": 92.45,
  "ter": 0.0020,
  "dividend_policy": "ACCUMULATING",
  "asset_allocation": {
    "equities": 0.98,
    "cash": 0.02
  },
  "holdings_count": 1500
}
```

## Fund as an Instrument

### holding_count


In the context of investment funds (such as ETFs or mutual funds), holding_count refers to the total number of individual securities held within the fund's portfolio.

#### Key Details

- **Measurement of Diversification**: It is a primary indicator of how diversified a fund is. For example, an S&P 500 index fund would typically have a *holding_count* near 500, while a global fund like the MSCI World might have a **holding_count** exceeding 1,500
- **Asset Allocation**: It represents the breadth of the fund across its targeted asset classes (equities, bonds, etc.).
- **Data Representation**: In financial data models, this value is used to give investors a quick snapshot of the fund's internal complexity without listing every individual asset.

##### Example

If an ETF has a holding_count of 1,500, it means the fund manager has distributed the fund's capital across 1,500 different stocks or bonds.

### Asset Allocation: Shape of a Fund

In a professional data model, Asset Allocation is rarely just a single number. It is typically modeled as an Array of Objects or a Nested Map that breaks the fund's internal portfolio down by percentage across different dimensions.

Because a fund can be categorized in multiple ways (by asset class, by region, or by sector), a robust model often includes several allocation "buckets."

#### In a professional data model, Asset Allocation is rarely just a single number. It is typically modeled as an Array of Objects or a Nested Map that breaks the fund's internal portfolio down by percentage across different dimensions.

Because a fund can be categorized in multiple ways (by asset class, by region, or by sector), a robust model often includes several allocation "buckets."

#### 1. Asset Class Allocation (The "What")

This is the most fundamental level. It tells the system the percentage of the fund held in different types of securities.

- **Logic**: The sum of all values must equal 1.0 (100%).
- **Key Categories**: EQUITY, FIXED_INCOME, CASH, REAL_ESTATE, COMMODITIES, OTHER.

#### 2. Regional Allocation (The "Where")

This models where the underlying companies or issuers are located. 

- **Structure**: Often follows ISO country codes (e.g., US, CH, DE) or broader regions (e.g., EMERGING_MARKETS, EUROZONE, NORTH_AMERICA).

- Purpose: Helps investors identify "Geographic Concentration Risk."

#### 3. Sector Allocation (The "Industry")

Specifically for Equity funds, this identifies which parts of the economy the fund is "betting" on.

- **Standard**: Most systems use the GICS (Global Industry Classification Standard).
- **Examples**: TECHNOLOGY, HEALTHCARE, FINANCIALS, ENERGY, CONSUMER_STAPLES.

#### Technical Data Model (JSON Example)

In an API like OpenWealth, the allocation is usually a sub-resource of the instrument. Here is how you would model it to be both human-readable and machine-processable:

```joson
{
  "instrument_id": "LU0360863863",
  "allocation": {
    "by_asset_class": [
      { "type": "EQUITY", "percentage": 0.65 },
      { "type": "FIXED_INCOME", "percentage": 0.30 },
      { "type": "CASH", "percentage": 0.05 }
    ],
    "by_region": [
      { "region": "NORTH_AMERICA", "percentage": 0.50 },
      { "region": "EUROPE", "percentage": 0.30 },
      { "region": "ASIA_PACIFIC", "percentage": 0.20 }
    ],
    "by_sector": [
      { "sector": "INFORMATION_TECHNOLOGY", "percentage": 0.22 },
      { "sector": "FINANCIALS", "percentage": 0.18 },
      { "sector": "OTHER", "percentage": 0.60 }
    ]
  }
}
```

#### Why is this modeled this way?

1. **Drill-Down Capability**: By modeling these as arrays, a portfolio management system can "look through" the fund. If you own 10 different funds, the system can calculate your total exposure to Apple or your total exposure to the US Dollar by summing up the percentages across all fund instruments.
2. **Rebalancing**: It allows algorithms to trigger alerts if a fund's allocation drifts too far from its stated goal (e.g., a "Balanced Fund" that accidentally becomes 90% stocks).
3. **Risk Analysis**: It enables "Stress Testing." For example, "How much of my portfolio is in the Energy sector if oil prices crash?"

### Asset Allocation: Top Holding Model

While high-level percentages (Stocks vs. Bonds) give you the "shape" of a fund, professional wealth management requires a "Look-Through" capability.

To achieve this, the data model for a fund instrument usually includes a specific section for Top Holdings.

#### The "Top Holdings" Model

Instead of listing every single position (which could be 3,000+ stocks in a global fund), the instrument model typically exposes the **Top 10** or **Top 20** holdings. These usually represent a significant portion of the fund's total risk.

##### Key Attributes for a Holding::

- **Security Identifier**: ISIN or Ticker of the underlying stock/bond.
- **Name**: The human-readable name (e.g., "NVIDIA Corp").
- **Weight**: The percentage of the fund's total AUM invested in this specific security.
- **Asset Class**: To confirm if the holding is an equity, bond, or derivative.

##### Why "Look-Through" Data is Critical

###### 1. The "Concentration" Trap

A fund might look diversified because it has 500 holdings, but if the **Top 10 holdings make up 50% of the fund**, it is actually highly concentrated. If one of those top companies fails, the fund will suffer significantly.

###### 2. Overlap Analysis

If you own three different "Growth Funds," you might unknowingly be "triple-exposed" to the same stock.

- **Fund A**: 8% Apple
- **Fund B**: 7% Apple
- **Fund C**: 5% Apple
- **Your Reality**: You have a massive, unintended bet on Apple that only a drill-down can reveal.

###### 3. Regulatory and Sustainability (ESG) Reporting

Investors often want to know if their funds hold specific types of companies (e.g., "Does this fund hold any oil companies?"). Without listing the top positions, you can't answer that question accurately.

##### Technical Data Model with "Top Holdings"

In an API response, the top_holdings attribute is modeled as an array of objects nested within the instrument's details:

```json
{
  "instrument_id": "US78462F1030",
  "name": "SPDR S&P 500 ETF Trust",
  "asset_allocation": {
    "equity": 0.998,
    "cash": 0.002
  },
  "top_holdings": [
    {
      "identifier": "AAPL",
      "name": "Apple Inc.",
      "weight": 0.071,
      "asset_class": "EQUITY"
    },
    {
      "identifier": "MSFT",
      "name": "Microsoft Corp.",
      "weight": 0.065,
      "asset_class": "EQUITY"
    },
    {
      "identifier": "NVDA",
      "name": "NVIDIA Corp.",
      "weight": 0.051,
      "asset_class": "EQUITY"
    }
  ]
}
```

### Levels of Portfolio Transparency

| Level | Data Provided | Purpose |
| :--- | :--- | :--- |
| **Level 1** | Total Asset Class (e.g., 60/40) | Strategic Asset Allocation. |
| **Level 2** | Region/Sector (e.g., 20% Tech) | Thematic and Geographic Risk. |
| **Level 3** | **Top Holdings (e.g., 7% Apple)** | **Specific Security Risk and Overlap.** |
| **Level 4** | Full Portfolio Disclosure | Full transparency (usually only in monthly reports). |

## The Fund Fees Model


To build a robust data model for fund fees, you need to account for three levels of costs: Ongoing Fees (internal to the fund), Transaction Fees (at the point of buy/sell), and Performance Fees (common in active or hedge funds).

Below is a structured JSON model that separates these concerns for clarity and scalability.

```json
{
  "fees": {
    "ongoing": {
      "ter": 0.0020,
      "management_fee": 0.0015,
      "admin_fee": 0.0005,
      "is_capped": true
    },
    "transactional": {
      "entry_load": 0.00,
      "exit_load": 0.00,
      "buy_sell_spread_est": 0.0008,
      "brokerage_fees": "Varies by platform"
    },
    "incentive": {
      "performance_fee": 0.00,
      "hurdle_rate": null,
      "high_water_mark": false
    },
    "tax_wrapper_costs": {
      "stamp_duty": 0.00,
      "withholding_tax_internal": "15% on US dividends"
    }
  }
}
```

### 1. Ongoing Fees (The "Hidden" Costs)

These are deducted from the fund's assets and are reflected in the NAV rather than billed to you.

- **ter** (Total Expense Ratio): The most important metric. It combines the management fee and operational costs (legal, audit).
- **management_fee**: The portion paid specifically to the fund manager (BlackRock, Vanguard, etc.).
- **is_capped**: Some managers promise that fees will not exceed a certain % even if operating costs spike.

### 2. Transactional Fees (The "Point of Entry" Costs)

These occur when you actually move money in or out.

- **entry_load / exit_load**: Common in Mutual Funds, rare in ETFs. This is a fee paid to the fund house just for joining or leaving.
- **buy_sell_spread_est**: Estimated spread between buy and sell prices, often due to market conditions.
- **brokerage_fees**: Varies by platform, often included in the TER for ETFs but separate for Mutual Funds.
- **withholding_tax_external**: Tax paid to the government on distributions to non-residents, typically 30%.

### 3. Incentive Fees (The "Alpha" Costs)

Mostly found in actively managed funds or alternative investments (Hedge Funds/Private Equity).

- **performance_fee**: A % of profits (e.g., 20%) taken by the manager if they beat a specific target.
- **high_water_mark**: A safeguard for investors ensuring the manager doesn't get a performance fee for simply recovering past losses.

#### Implementation Advice

- **Scale**: Always store fees as decimals (e.g., 0.0020 for 0.20%) to avoid rounding errors in calculations.
- **Inheritance**: If you are building a database, link the brokerage_fees to the Account/Platform level rather than the Fund level, as the same ETF will cost different amounts to trade on Vanguard vs. Fidelity.


## Legal Structure

The Issuer and the Legal Structure are distinct concepts in a fund's data model. Think of the Issuer as the "Brand/Manufacturer" and the Legal Structure as the "Legal Blueprint" or "Container."

In your specific example of the iShares Core MSCI World, **BlackRock** (the Issuer) uses an **Irish ICAV** (the Legal Structure) to house the fund.

### 1. Issuer vs. Legal Structure

### 2. The "Umbrella" Construct

In professional data models, there is often a third layer called the **Umbrella**. This is because a single legal entity (like a SICAV) can contain dozens of different funds (Sub-funds).

#### Recommended Data Model Expansion

````joson
{
  "instrument_id": "IE00B4L5Y983",
  "issuer": "BlackRock",
  "legal_framework": "UCITS", 
  "legal_structure": "ICAV",
  "umbrella_name": "iShares VII plc",
  "domicile": "Ireland"
}
````

- $legal_framework$: (e.g., **UCITS**) This tells the investor the "gold standard" of European retail protection.
- $legal_structure$: (e.g.,** SICAV** or **ICAV**) This tells the investor if the fund is a "company" they own shares in or a "contract" they own units of. 
- $umbrella_name$: This is the actual legal name of the entity that appears in the prospectus. For most iShares ETFs, the umbrella is often something like iShares IV plc or iShares VII plc.
- $domicile$: The country where the fund is registered (e.g., Ireland, Luxembourg, USA). This is vital for understanding tax withholding.

### 3. Why the distinction matters

- **Insolvency Protection**: : The "Legal Structure" ensures that if the Issuer (BlackRock) goes bankrupt, your assets are safe because they are held in a separate legal entity (the Umbrella) with a third-party custodian.
- **Taxation**: An Irish **ICAV** structure handles US dividend tax differently than a French **FCP** structure.
- **Regulatory Access**: A UCITS structure can be sold to retail investors across Europe, whereas a Limited Partnership (LP) structure is usually restricted to professional/institutional investors.

> **Pro Tip**: If you are building a database for European funds, UCITS is the most important "Legal Framework" tag to include, as it acts as a passport for the fund to be sold across borders.

