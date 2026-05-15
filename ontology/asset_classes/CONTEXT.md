# Asset Class Context

This file contains the context for the asset class domain in the advisory data ontology.

## 1. The Hierarchy of Classification

A PMS doesn’t just see "Stock" or "Bond." It uses a multi-layered hierarchy to help managers drill down into specific exposures.

- **Broad Asset Class**: The highest level (e.g., Equities, Fixed Income, Alternatives, Cash).
- **Sub-Asset Class**: A more granular look (e.g., Developed Markets vs. Emerging Markets, or Government Bonds vs. Corporate Bonds).
- **Security Type**: The specific instrument (e.g., Common Stock, Preferred Stock, Treasury Bill).

## 2. Data Mapping and Valuation

Each asset class has unique data requirements. The PMS must be programmed to handle these different "math problems" simultaneously:

| Asset Class | Key Data Points Required | Valuation Method |
| :--- | :--- | :--- |
| **Equities** | Ticker, Exchange, Dividend Yield | Market Price × Quantity |
| **Fixed Income** | Coupon Rate, Maturity Date, Credit Rating | Present Value of Cash Flows |
| **Derivatives** | Strike Price, Expiration, Underlying Asset | Options Pricing Models (e.g., Black-Scholes) |
| **Real Estate** | Appraisal Date, Net Operating Income | Periodic Appraisal / Book Value |

## 3. Risk and Compliance Engines

The system uses asset classes to enforce Investment Policy Statements (IPS). If a client’s profile says they cannot have more than 20% in "High-Yield Bonds," the PMS flags a "Compliance Breach" the moment a trade pushes the portfolio over that limit.

It also calculates risk metrics based on these classes, such as:

- **Correlation**: How different classes move in relation to each other.
- **Volatility**: The standard deviation of returns for a specific class.
- **Beta**: The sensitivity of an equity class relative to the overall market.

## 4. Performance Attribution

When a portfolio outperforms its benchmark, the PMS uses Brinson Attribution to figure out why. It breaks down the "Alpha" (excess return) into two main categories:

1. **Selection Effect**: Did you pick better individual stocks than the benchmark?
2. **Allocation Effect**: Did you put more money into the "right" asset classes (e.g., overweighting Tech when it was booming)?

## 5. Integrating "non-traditional" assets

Integrating "non-traditional" assets like Private Equity (PE) or Cryptocurrency into a PMS is a challenge because they break the standard "daily liquid price" model. The system has to switch from automated data feeds to manual or "stale-price" logic.

Here is how these two distinct worlds are handled:

### 1. Private Equity: The "Commitment" Model

Private equity doesn't trade on an exchange, so the PMS cannot simply pull a price. Instead, it tracks the **Lifecycle of the Investment**.

- **Capital Commitments**: The system tracks the total amount a manager has pledged (e.g., $1M). This is a "memo" item—it doesn't affect the current value but impacts "Dry Powder" reports.
- **Capital Calls (Drawdowns)**: When the PE fund needs money, the PMS records a cash outflow and an increase in the cost basis of the asset.
- **Stale Pricing (Lagged Valuations)**: PE valuations usually come from Quarterly Capital Accounts. A PMS will carry the "Last Price" for 90 days. This creates a "smoothing" effect where the portfolio looks less volatile than it actually is.
- **IRR vs. TWR**: Standard stocks use Time-Weighted Return (TWR). For PE, the PMS must calculate Internal Rate of Return (IRR) because the investor controls the timing of the cash flows.

### 2. Cryptocurrency: The "Always-On" Challenge

Unlike PE (which is slow), Crypto is too fast for many legacy PMS platforms.

- **24/7 Pricing**: Most PMS systems are built for a 4:00 PM EST "Market Close." Crypto never closes. The system must be configured to take a "Snapshot" at a specific GMT time to align with the rest of the portfolio.
- **Custody Integration**: Instead of a traditional prime broker (like Goldman Sachs), the PMS must bridge to digital custodians (like Coinbase or Fireblocks) or pull directly from on-chain wallets via API.
- **Fractional Shares**: While a stock PMS might be used to 4 decimal places, Crypto often requires 8 to 18 decimal places (e.g., Satoshi units). If the system isn't "High-Precision" ready, it will round off significant value.

### 3. Comparison of Integration Methods

| Feature | Private Equity | Cryptocurrency |
| :--- | :--- | :--- |
| **Pricing Frequency** | Quarterly (Manual) | Real-time (API) |
| **Liquidity Profile** | Illiquid (Lock-up periods) | Highly Liquid |
| **Primary Metric** | Multiple on Invested Capital (MOIC) | Spot Price / Volatility |
| **System Entry** | Manual "Shadow Accounting" | Direct Wallet/Exchange Feed |

### 4. Why This Matters for the Portfolio Manager

When these assets are integrated, the PMS creates a "Total Wealth View." Without this, a manager might think a portfolio is 60/40 Stocks/Bonds, failing to realize they actually have a 10% "hidden" risk in illiquid Private Equity or high-volatility Crypto.

> In a professional PMS, Private Equity is often kept in a "Side Pocket." This prevents the quarterly valuation jumps from distorting the daily performance metrics of the liquid part of the portfolio.

## Functional model for Asset Class Domain

To build a functional model for asset classes in a PMS, the Asset Class acts as the "middleman" between the raw market data (CFI) and the human-readable reports.

### 1. The Core Data Model (Schema)

When defining the "Asset Class" object in your system, it needs to capture more than just a name. It requires behavioral attributes that tell the system how to treat the money.

| Property | Data Type | Description |
| :--- | :--- | :--- |
| `AssetClassID` | String (UUID) | Unique identifier for the system. |
| `DisplayName` | String | How it appears on client reports (e.g., "Emerging Market Debt"). |
| `ParentClassID` | String | Used for hierarchical roll-ups (e.g., linking "US Tech" to "Equities"). |
| `LiquidityDays` | Integer | Standard settlement time (e.g., 2 for T+2). |
| `ValuationFrequency` | Enum | Daily, Monthly, Quarterly, or Ad-hoc. |
| `BaseCurrency` | ISO Code | The default currency for risk/performance calc. |
| `IsRiskFree` | Boolean | Defines if this class is used as the benchmark for Sharpe Ratios. |


### 2. Defining the Logic Tree (The Mapping)

This is the "brain" of your model. You define rules that automatically categorize a security based on its **CFI code** and **ISO Country Code**.

- **Rule A**: If CFI starts with E (Equities) AND Country = US → **Domestic EquityRule**
- **Rule B**: If CFI starts with D (Debt) AND Maturity < 1 Year → **Cash Equivalents**
- **Rule C**: If CFI starts with O (Options) OR F (Futures) → **Derivatives**

### 3. Handling Valuation Methods

Your model must define a "Pricer" for each class. This is critical for the "Private Equity vs. Crypto" problem.

- **Market-to-Market (MtM)**: Used for Equities/Crypto. The system pulls the latest last_price from a feed.
- **Market-to-Model (MtMod)**: Used for complex Bonds or OTC Derivatives. The system calculates value based on yield curves or Black-Scholes.
- **Last-Appraisal**: Used for Private Equity/Real Estate. The system holds the price constant until a manual update is keyed in.

- **Expected Return**: (e.g., 7% for Equities).
- **Standard Deviation**: (e.g., 15% for Equities).
- **Correlation Matrix**: A table defining how this class moves relative to others (e.g., Gold vs. S&P 500).

### 4. Analytical Attributes

For the model to be useful for a Portfolio Manager, it needs to store "Assumptions" for forward-looking projections:

- **Expected Return**: (e.g., 7% for Equities).
- **Standard Deviation**: (e.g., 15% for Equities).
- **Correlation Matrix**: A table defining how this class moves relative to others (e.g., Gold vs. S&P 500).

### 5. Implementation Example (JSON)

```json
{
  "class_name": "High Yield Corp Debt",
  "super_class": "Fixed Income",
  "cfi_prefix": "DB",
  "valuation_logic": "Yield_To_Maturity",
  "risk_weight": 0.18,
  "tax_status": "Interest_Income",
  "allow_shorting": true,
  "default_benchmark": "JPM_HY_INDEX"
}
```

> A common mistake is making the model too rigid. Markets evolve (e.g., 10 years ago, "Digital Assets" didn't exist in most PMS models).

### "Hybrid" Assets
Tto define a "Hybrid" asset class, we have to look at how a system handles a security that acts like a **Bond** one day and a **Stock** the next.

A "Hybrid" model is essentially a conditional logic layer that sits between your Fixed Income and Equity definitions. Here is how you structure that model:

#### 1. The "Delta-Based" Classification

In a professional PMS, the system doesn't just "pick" a category. It uses a **Delta Trigger**.

- **Debt-Like Phase**: When the underlying stock price is low, the security is "Out-of-the-Money." The PMS treats it as **Fixed Income** (focusing on coupon and credit risk).
- **Equity-Like Phase**: When the stock price rises, the conversion feature becomes valuable. The PMS "re-sleeves" the asset into Equities because its price movement is now 90% correlated with the stock.


#### 2. Defining the Hybrid Schema

When you build the model for these assets, you need specific fields that standard stocks or bonds don't have:

| Field Name | Data Type | Purpose |
| :--- | :--- | :--- |
| `ConversionRatio` | Decimal | How many shares you get per bond. |
| `StrikePrice` | Currency | The "inflection point" where it becomes Equity. |
| `Delta` | 0.0 to 1.0 | The sensitivity to the underlying stock. |
| `BondFloor` | Currency | The theoretical value if the conversion was worthless. |

#### Understanding Convertible Bonds

The fields in this table relate specifically to **Convertible Bonds**, which are hybrid securities that can be changed into a predetermined number of shares of the issuing company's stock.

- **Bond Floor**: This represents the investment value of the bond if it had no conversion feature, providing a "safety net" for the investor.
- **Delta**: Much like in options trading, this measures how much the convertible bond's price is expected to move relative to a $1 change in the underlying stock price.

### 3. The CFI Mapping for Hybrids

This is where your CFI logic becomes powerful. Hybrids usually start with specific codes that tell the system to look for "extra" data:

- DB\X\X\X\X: Standard Debt (Fixed Income).
- DC\X\X\X\X: Convertible Debt (Trigger Hybrid Logic).
- EP\X\X\X\X: Preferred Shares (Equity, but with a fixed dividend—often modeled as **Hybrid**).

Since you're ready to define a "Hybrid" asset class, we have to look at how a system handles a security that acts like a Bond one day and a Stock the next.

A "Hybrid" model is essentially a conditional logic layer that sits between your Fixed Income and Equity definitions. Here is how you structure that model:

1. The "Delta-Based" Classification
In a professional PMS, the system doesn't just "pick" a category. It uses a Delta Trigger.

Debt-Like Phase: When the underlying stock price is low, the security is "Out-of-the-Money." The PMS treats it as Fixed Income (focusing on coupon and credit risk).

Equity-Like Phase: When the stock price rises, the conversion feature becomes valuable. The PMS "re-sleeves" the asset into Equities because its price movement is now 90% correlated with the stock.

2. Defining the Hybrid Schema
When you build the model for these assets, you need specific fields that standard stocks or bonds don't have:

Field Name	Data Type	Purpose
ConversionRatio	Decimal	How many shares you get per bond.
StrikePrice	Currency	The "inflection point" where it becomes Equity.
Delta	0.0 to 1.0	The sensitivity to the underlying stock.
BondFloor	Currency	The theoretical value if the conversion was worthless.
3. The CFI Mapping for Hybrids
This is where your CFI logic becomes powerful. Hybrids usually start with specific codes that tell the system to look for "extra" data:

DBXXXX: Standard Debt (Fixed Income).

DCXXXX: Convertible Debt (Trigger Hybrid Logic).

EPXXXX: Preferred Shares (Equity, but with a fixed dividend—often modeled as Hybrid).

### 4. The "Sleeve" Approach

Most sophisticated systems use Virtual Sleeves to report on hybrids.

- **The Accounting Sleeve**: Always treats it as a Bond (for tax and interest reasons).
- **The Risk Sleeve**: Splits the value. For example, if a Convertible Bond has a Delta of 0.6, the system reports it as **60% Equity Exposure** and **40% Fixed Income Exposure**.

### 5. Implementation: The Logic Gate

To implement this, your system's "Classifier Engine" should follow this flow:

**IF* CFI_Category == 'D' **AND** Has_Conversion_Feature == **TRUE**:

1. Mark as **AssetClass**: *Hybrid*.
2. Calculate *Current_Delta* against *Underlying_Ticker*.
3. IF Delta > 0.8, Roll-up to Equity_Reports.
4. ELSE, Roll-up to Fixed_Income_Reports.

## Compliance Rules

When you move from defining asset classes to enforcing Compliance Rules, you are essentially turning your data model into a "policeman." In a PMS, **compliance rules** ensure the portfolio stays within the boundaries of the **Investment Policy Statement (IPS)** or regulatory requirements.

For **Hybrid** assets, compliance is tricky because their nature shifts. You have to decide if you are monitoring them based on their Legal Form (it's a bond) or their **Economic Exposure** (it acts like a stock).

### 1. Types of Compliance Rules1. 

Your system should support three primary levels of "Checks":

- **Hard Limits**: The system blocks the trade entirely (e.g., "No tobacco stocks").
- **Soft Limits**: The system triggers a warning/alert to the Chief Compliance Officer (e.g., "Cash is below 2%").
- **Pre-Trade vs. Post-Trade**: Pre-trade prevents the mistake; Post-trade catches drifts caused by market movement.

### 2. Rule Architecture for Hybrid Assets

Because Hybrids (like Convertibles or Preferreds) live in two worlds, your compliance engine needs "Look-Through" logic.

#### A. The "Bucket" Rule (Allocation Limits)

This is the most basic rule. You set a maximum percentage for the Asset Class.

- **Rule**: Sum(Hybrid_Assets) / Total_Portfolio_Value <= 15%
- **The Hybrid Twist**: If a Convertible Bond's Delta rises to 0.9, does it still count toward the 15% "Hybrid" bucket, or does it now count toward the 60% "Equity" bucket? Most systems use **Fixed Categorization** for bucket limits to avoid "accidental" breaches just because a stock price went up.

#### B. The Concentration Rule (Issuer Limit)

You cannot be too exposed to one company.

- **Rule**: (Common_Stock_A + Convertible_Bond_A) / Total_Portfolio <= 5%
- **Logic**: The system must aggregate different asset classes by the **Ultimate Issuer ID** (e.g., if you own Tesla stock and Tesla convertible bonds, the system must sum them together).

#### C. The Rating Rule (Credit Quality)

Hybrids are often unrated or sub-investment grade.

- **Rule**: If AssetClass == 'Hybrid' AND CreditRating < 'BBB', Max_Allocation = 5%

### 3. Compliance Rule Schema (Logic Example)

To build this in your system, a rule isn't just a sentence; it’s a set of parameters.

| Parameter | Example Value |
| :--- | :--- |
| **Rule ID** | `LIMIT_HYBRID_CONCENTRATION` |
| **Scope** | `Portfolio_Level` |
| **Calculation Base** | `Market_Value_Percentage` |
| **Operator** | `LESS_THAN_OR_EQUAL_TO` |
| **Threshold** | `10.00` |
| **Grouping Key** | `AssetClass == 'Hybrid'` |

#### Understanding Concentration Limits

The data in this table represents a **Compliance Rule** definition used in portfolio management systems. This specific rule is designed to manage risk by limiting exposure to a specific asset category:

- **Scope**: The rule is applied across the entire Portfolio rather than individual accounts.
- **Logic**: It calculates the total market value of all assets where the class is "Hybrid" and ensures they do not exceed a **10% threshold** of the total portfolio value.
- **Purpose**: This prevents "concentration risk," ensuring the portfolio remains diversified and isn't overly dependent on higher-risk hybrid instruments.

### 4. Dealing with "Passive Breaches"

A "Passive Breach" happens when you didn't buy anything new, but the market moved.

- **Scenario**: You have a 10% limit on Hybrids. You own a Convertible Bond. The underlying stock rockets up 50%. Your Hybrid allocation is now 12%.
- **System Action**: The PMS flags a **Post-Trade Breach**. The compliance model must define a "Cure Period" (e.g., the manager has 5 days to sell down the position or seek a waiver).

### 5. Regulatory Compliance (CFI-Based)

Regulators often use CFI codes to define what you can and cannot hold.

- **Rule**: "No Unlisted Equities."
- **System Logic**: IF CFI_Char_1 == 'E' AND CFI_Char_4 == 'N' (Non-listed/Private), THEN BLOCK_TRADE.

## Implementation Decisions

When building these rules, you need to decide on Aggregation Logic:

Should your compliance engine calculate limits based on Notional Value (the face value of the bond) or Market Value (the current price)? For hybrids, Market Value is standard, but for derivatives, Notional is usually required by regulators.

## Aggregation Logic

To build aggregation logic, you are essentially creating a "Group By" engine that can look at the same set of data through different lenses. In a PMS, you don’t just sum up the market value; you must define what you are summing and how you handle the "dirty" data (like pending trades or accrued interest).

Here is the architectural blueprint for building an aggregation engine.

### 1. Define the "Aggregation Dimensions"

An aggregation is defined by its Keys. You need to allow the system to group data dynamically based on your asset class model.

- **Entity Level**: Fund -> Portfolio -> Sleeve.
- **Asset Level**: Asset Class -> Sub-Class -> CFI Group -> Issuer.
- **Risk Level**: Country -> Currency -> Credit Rating.

### 2. The Logic Flow (The "Pipeline")

A robust aggregation engine follows a four-step process to ensure the numbers are accurate before they are summed.

#### Step A: Value Normalization

Before summing, every asset must be converted to the Portfolio Base Currency.
- Logic: Position_Value * FX_Rate(Asset_CCY, Portfolio_Base_CCY)

#### Step B: The "What" (Exposure Type)

You must define which "Value" you are aggregating. This is critical for Compliance:

1. **Market Value (MV)**: Price × Quantity. (Standard for Equity)
2. **Gross Notional (GNV)**: The underlying value. (Standard for Derivatives/Hybrids)
3. **Net Exposure**: Longs minus Shorts.

#### Step C: The Filter (The "Predicate")

You define the subset of data.

- Example: "Aggregate all assets where CFI_Char_1 == 'D' (Debt) and Maturity_Date < 1 Year."

### 3. Implementation: The Pseudo-Code Logic

If you were building this in a functional way, your aggregation function would look like this:

```python
def aggregate_exposure(portfolio, group_by_key, value_type="MarketValue"):
    # 1. Fetch all positions
    positions = portfolio.get_all_positions()
    
    # 2. Initialize the result map
    aggregation_results = {}

    for pos in positions:
        # Get the grouping label (e.g., 'Hybrid', 'Equity', 'Fixed Income')
        group_label = pos.get_attribute(group_by_key)
        
        # Calculate the value in Base Currency
        val = pos.calculate_value(value_type) * pos.fx_rate_to_base
        
        # Add to the bucket
        if group_label in aggregation_results:
            aggregation_results[group_label] += val
        else:
            aggregation_results[group_label] = val
            
    return aggregation_results
```

### 4. Advanced Aggregation: The "Look-Through"

This is the "Pro" level of aggregation. If a portfolio owns an **ETF (Exchange Traded Fund)**, a simple aggregation would put 100% of that value into "Equities."

A **Look-Through Aggregator** ignores the ETF "shell" and aggregates the underlying components:

- **Asset**: SPY (S&P 500 ETF) - $1,000,000
- **Logic**: Aggregate $70,000 to "Tech Sector"
  - Aggregate $120,000 to "Financials"
  - Aggregate $30,000 to "Cash" (held within the fund)

### 5. Aggregation Table for Compliance

In your database, the output of an aggregation run for a Hybrid-heavy portfolio would look like this:

| Grouping Key (Asset Class) | Market Value (USD) | % of Total | Weighted Avg Beta |
| :--- | :--- | :--- | :--- |
| **Domestic Equity** | $5,000,000 | 50% | 1.1 |
| **Fixed Income** | $3,000,000 | 30% | 0.2 |
| **Hybrid (Convertibles)** | $1,500,000 | 15% | 0.65 |
| **Cash** | $500,000 | 5% | 0.0 |
| **TOTAL** | **$10,000,000** | **100%** | **0.78** |

#### Understanding Portfolio Beta

The final row of your table shows a **Weighted Average Beta of 0.78**. In finance, Beta measures the volatility (or systematic risk) of a portfolio in comparison to the market as a whole (usually the S&P 500, which has a Beta of 1.0).

- **Beta > 1.0**: The portfolio is more volatile than the market.
- **Beta < 1.0**: The portfolio is less volatile than the market.
- **Your Portfolio (0.78)**: This suggests a relatively conservative stance, likely due to the significant 35% allocation in Fixed Income and Cash.

## Exclusion Logic

Exclusion logic is critical because if you aggregate "everything," your compliance reports will be full of "noise." For example, if you have a rule that says "Equity cannot exceed 60%," but your system includes **Pending Cash from a Stock Sale** in that calculation, your data is lying to you.

Here is how to build an Exclusion Engine for your aggregation logic.

### 1. Defining "Exclusion Categories"

You need to categorize assets that should be "invisible" to certain rules. In a PMS, these are usually defined by their **Transaction Status** or **Instrument Type**.

- **Cash Collateral**: Money tied up as a "security deposit" for a derivative trade. It shouldn't count as "Spendable Cash."
- **Accrued Interest**: Money you've earned on a bond but haven't received yet. It’s an asset, but not "Principal."
- **Pending Trades (The "Settlement Gap")**: Trades that are "Executed" but not yet "Settled."
- **Corporate Actions**: Stock splits or mergers that are in a "Suspense" account.
- **Derivative Collateral**: Money tied up as collateral for a derivative trade. It shouldn't count as "Spendable Cash."

### 2. The Exclusion Schema: "The Filter Array"

Instead of hard-coding exclusions, your aggregation logic should look for a **Filter Array**. When a compliance rule is called, it passes a list of "Do Not Include" tags to the aggregator.

| Rule Type | Aggregation Base | Exclusions (Filter Tags) |
| :--- | :--- | :--- |
| **Equity Limit** | Market Value | `Status: Pending`, `Type: Accrual` |
| **Cash Floor** | Liquidity Value | `Status: Collateralized`, `Type: Restricted` |
| **Issuer Limit** | Total Exposure | `Type: Dividend_Receivable` |

#### Understanding Compliance Exclusions

This table outlines the logic for filtering specific data points out of compliance calculations to ensure accuracy:

- **Equity Limit** : This rule uses M**arket Value** as its base but excludes pending trades or accruals, likely to ensure it only calculates based on settled, "real" positions.
- **Cash Floor**: When checking for minimum liquidity, the system ignores cash that is already **Collateralized** or **Restricted**, as that money cannot be easily withdrawn.
- **Issuer Limit**: When calculating how much exposure you have to a single company, it excludes **Dividend Receivables** (money owed but not yet received) to focus on the primary investment risk.

### 3. Implementing the Logic Gate

In your code or system logic, the exclusion happens at the Iterator level. You want to "Skip" the asset before it ever hits the "Sum" function.

```python
def aggregate_with_exclusions(positions, exclusions_list):
    total_val = 0
    for pos in positions:
        # Check if the raw_data has a 'tag' that is in our exclusion list
        if any(tag in pos.tags for tag in exclusions_list):
            continue  # Skip this raw_data entirely
        
        # Check for technical exclusions (e.g., zero-value or cancelled trades)
        if pos.quantity == 0 or pos.status == 'CANCELLED':
            continue
            
        total_val += pos.market_value_base
    return total_val
```

### 4. The "Wash Account" Problem

A major part of exclusion logic is handling Wash Accounts. These are temporary system accounts used to move money. If you don't exclude these, you might "Double Count" your assets.

#### Example:

1. You sell $100k of Apple stock.
2. The $100k leaves the **Equity Sleeve**.
3. The $100k enters a **Settlement Suspense Account**.
4. 3 days later, the $100k enters the **Cash Account**.

### 5. Visualizing the Result

When your engine runs with proper exclusion logic, your compliance dashboard should show the "Gross" vs. "Net" view:

| Asset | Total Value (Gross) | Exclusion Reason | Aggregated Value (Net) |
| :--- | :--- | :--- | :--- |
| **Apple Inc.** | $1,000,000 | None | $1,000,000 |
| **US Treasury** | $500,000 | None | $500,000 |
| **Cash (Margin)** | $200,000 | **Restricted Collateral** | $0 |
| **Accrued Divs** | $5,000 | **Non-Principal** | $0 |
| **FINAL SUM** | **$1,705,000** | | **$1,500,000** |

#### Understanding the Reconciliation

This table demonstrates a common **Net Asset Value (NAV)** or **Regulatory Capital** calculation where certain line items are excluded from the final sum based on their risk or liquidity profiles:

- **Gross Total**: The simple sum of all account balances ($1,705,000).
- **Net Aggregation**: Only include primary, unrestricted assets.
  - **Margin Cash** is excluded because it is "Restricted Collateral" held against other obligations.
  - **Accrued Dividends** are excluded because they are "Non-Principal" and haven't been settled as cash yet.
- **Final Result**: A more conservative $1,500,000 figure used for actual investment or compliance limits.

## Performance in a PMS

In performance reporting, the "total return" of an asset class is rarely enough for a portfolio manager. They need to know how that return was generated. This is where you separate **Income** (yield) from **Growth** (capital appreciation).

In a PMS, this logic is essential for tax planning and for evaluating the "carry" of a portfolio versus its market sensitivity.

### 1. The Mathematical Components

To build this logic, your system must track three distinct data streams for every asset:

- **Capital Growth ($\Delta P$)**: The change in the market price of the asset.
- **Realized Income ($I$)**: Cash actually received (Dividends, Bond Coupons).
- **Accrued Income ($A$)**: Income earned but not yet paid (e.g., the interest a bond builds up between payment dates).

The Total Return formula in your system logic would look like this:

$$Total\ Return = \frac{(P_{end} - P_{start}) + Income + \Delta Accrued}{P_{start}}$$

### 2. Defining the "Income vs. Growth" Attributes

When you define your asset class model, you must assign "Income Behaviors."

| Asset Class | Primary Return Driver | Income Logic |
| :--- | :--- | :--- |
| **Equities** | Growth | Dividends (Discrete events) |
| **Fixed Income** | Income | Coupons (Continuous accrual) |
| **Real Estate** | Income | Rental Yield (Monthly/Quarterly) |
| **Crypto** | Growth | Staking Rewards (Variable) |

#### Understanding Return Drivers and Income Logic

This classification system helps distinguish how different assets generate value for an investor:

- **Growth-Driven Assets**: Equities and Crypto primarily aim for capital appreciation. Income (dividends or staking) is secondary.
- **Income-Driven Assets**: Fixed Income and Real Estate are often held specifically for their steady cash flow
- **Accrual Differences**:
  - **Discrete**: Dividends are paid on specific dates and do not "grow" between payments.
  - **Continuous**: Bond coupons technically accrue daily, which is reflected in the "dirty price" of a bond.

### 3. The Performance Logic: "The Split"

Your system needs a process to decompose the total return. Here is how the logic handles a single asset (e.g., a stock that pays a dividend):

1. **Price Return**: Calculate the difference between the Beginning Market Value (BMV) and Ending Market Value (EMV), excluding cash flows. 
2. **Income Return**: Sum all dividends/coupons received during the period.
3. **Currency Return**: If the asset is in a foreign currency, isolate the gain/loss caused solely by the exchange rate.

### 4. Implementation: The Attribution Table

A professional PMS will output a table that looks like this for each asset class:

| Asset Class | Total Return | Growth (%) | Income (%) | FX Impact (%) |
| :--- | :--- | :--- | :--- | :--- |
| **US Equities** | 12.5% | 10.2% | 2.3% | 0.0% |
| **EM Bonds** | 4.2% | -1.5% | 6.5% | -0.8% |
| **Hybrid** | 8.0% | 4.0% | 4.0% | 0.0% |

#### Understanding Return Attribution

This table provides a performance attribution breakdown, showing exactly how each asset class arrived at its **Total Return**.

- **Total Return Calculation**: In this model, Total Return is the sum of Growth, Income, and FX Impact.
  -  Example (EM Bonds): $$-1.5\% \text{ (Growth)} + 6.5\% \text{ (Income)} - 0.8\% \text{ (FX Impact)} = 4.2\% \text{ (Total Return)}$$.
- **Income Performance**: EM Bonds (Emerging Market Bonds) are the strongest income providers at 6.5%, which offset significant losses in both capital growth and unfavorable currency movements.
- **FX Impact**: This measures how changes in foreign exchange rates affected the value of the investment when converted back to the base currency. The -0.8% for EM Bonds suggests the local currency weakened against the investor's home currency during the period.

### 5. Handling Reinvestment

Your system must also decide how to treat **reinvested income**.

- If a dividend is paid and immediately used to buy more shares, is that "Income" or "Growth"?
- **The Standard Logic**: It is tracked as **Income** at the moment of the event, and then any subsequent price movement on those new shares is tracked as **Growth**.

## Tax-Aware Performance

Building a **Tax-Aware Performance Engine** requires shifting from "market value" to "after-tax value." This is where the asset class model you built earlier becomes highly specialized, as the system must apply different tax treatments based on the Income Type (e.g., Qualified Dividends vs. Ordinary Interest).

Here is how to build the tax logic into your performance engine:

### 1. The Tax Attribute Layer

You must extend your Asset Class model to include **Tax Characterization**. The system uses these tags to determine which rate to "hit" the returns with.

| Asset Class | Primary Income Tax | Capital Gains Tax |
| :--- | :--- | :--- |
| **Municipal Bonds** | 0% (Tax-Exempt) | Short/Long-term Rates |
| **US Equities** | Qualified Rate (e.g., 15-20%) | Short/Long-term Rates |
| **REITs / Hybrids** | Ordinary Income (High) | Varies by Structure |
| **Crypto** | N/A (Usually no income) | Short-term (Property) |

#### Understanding After-Tax Returns

This table is critical for calculating **After-Tax Returns**, as the "sticker price" return on an asset often differs significantly from what an investor actually keeps.

- **Tax-Efficiency**: Municipal Bonds are highly efficient for income because they are often exempt from federal (and sometimes state) taxes.
- **Income Characterization**: The tax rate for REITs and Hybrids is typically higher because it is treated as **Ordinary Income**, whereas US Equities may benefit from lower **Qualified Dividend** rates.
- **Crypto Treatment**: Currently, most jurisdictions treat Cryptocurrency as **Property**, meaning every trade is a taxable capital gains event rather than an income event.

### 2. Calculating "Net-of-Tax" Returns

The engine performs a "shadow calculation." It keeps the gross performance but subtracts a **ax Liability Accrual** for every dollar of gain or income.

#### The Formula:

$$
Return_{Net} = \frac{(G_{unrealized} \times (1-t_{cg})) + (G_{realized} \times (1-t_{cg})) + (I \times (1-t_i))}{BMV}
$$

- $t_{cg}$: Capital Gains Tax Rate
- $t_i$: Income Tax Rate

### 3. Realized vs. Unrealized Tax Logic

To be accurate, your system must distinguish between taxes you **already owe** and taxes you **will owe**:

- **Realized Tax (The "Check already written")**: Triggered by a sale or a dividend payment. The system deducts this from the cash balance immediately.
- **Unrealized Tax (The "Deferred Liability")**: The system looks at your "Open Lots" (positions you still hold). If you bought Apple at $100 and it’s now $150, the system calculates a 15% tax on that $50 gain and "earmarks" it as a liability.

### 4. Tax-Loss Harvesting Logic

This is the most "intelligent" part of the engine. The system looks for opportunities to offset gains with losses to improve the net performance.

- **The Aggregator's Role**: The engine sums all realized gains and realized losses across the portfolio.
- **Asset Class Mapping**: It ensures you aren't trying to offset a "Capital Loss" against "Ordinary Income" (which tax authorities often restrict).
- **Wash Sale Detection**: The system flags if you sell a stock for a loss but buy it back within 30 days, which would disqualify the tax benefit.

### 5. Implementation: The Tax-Adjusted Attribution Table

Your output should now show the "Tax Drag"—the difference between what the market gave the manager and what the client actually keeps.

| Asset Class | Gross Return | Tax Drag | Net-of-Tax Return |
| :--- | :--- | :--- | :--- |
| **High Yield Bonds** | 7.0% | -2.8% (Ordinary) | 4.2% |
| **Growth Stocks** | 12.0% | -1.8% (Deferred CG) | 10.2% |
| **Muni Bonds** | 3.5% | 0.0% (Exempt) | 3.5% |

#### Understanding Tax Drag

"Tax drag" represents the portion of your potential return lost to taxes. As shown in the table above, the impact varies significantly based on how the government treats the income:

- **Ordinary Income**: High Yield Bonds suffer the most significant drag (-2.8%) because interest is typically taxed at your full marginal income tax rate.
- **Deferred Capital Gains (CG)**: Growth Stocks are more "tax-efficient" because you only pay taxes when you sell the asset. This allows more of your money to stay invested and compound over time. 
- **Tax-Exempt**: Municipal (Muni) Bonds have zero tax drag because their interest income is not subject to federal taxes, making their gross and net returns identical.

## Tax-Optimized Rebalancer

With tax-aware data, your "Rebalancing" logic changes. Instead of just selling an asset because it's "overweight," the system can now ask: "Is the tax cost of selling this position higher than the benefit of being perfectly balanced?"

A **Tax-Optimized Rebalancer** is the "holy grail" of automated portfolio management. It moves away from simple mathematical rebalancing (selling what is up, buying what is down) and treats tax as a transaction cost.

### 1. The Decision Engine: "The Tax-Cost-Benefit Analysis"

Instead of a binary "Overweight = Sell" logic, the rebalancer uses a Trade-Off Function. For every potential trade, it calculates:

1. Tracking Error Cost: The risk of not trading (how far are we from the target?).
2. Tax Cost: The immediate cash outflow from realizing a gain.

> The Logic Rule: Only execute the trade if **(Benefit of Risk Reduction) > (Cost of Tax Paid)**.

### 2. Tax-Lot Sorting (The "HIFO" Method)

When the system decides to sell an asset class, it doesn't just sell "100 shares." It looks at the individual "lots" (the history of when you bought the asset). To optimize taxes, the rebalancer uses specific accounting methods:

- **HIFO (Highest In, First Out)**: Sells the shares you bought at the highest price first to minimize the gain (or maximize the loss).
- **LIFO (Last In, First Out)**: Sells the shares you bought most recently first, which can be beneficial if you expect future price increases.
- **Specific Lots**: Allows for more granular control over which specific lots are sold, based on tax implications and investment goals.
- **MinTax**: A more complex algorithm that prioritizes selling lots with **Short-Term Losses** first, then **Long-Term Losses**, then **Long-Term Gains**.

### 3. The "Tolerance Band" Strategy

o prevent the system from "churning" the portfolio (trading too often and generating small tax bills), you define **Tolerance Bands** around your asset classes.

- **Target**: 40% Equities.
- **Band**: +/- 5%.
- **Rebalance Trigger**: The system only calculates a tax-optimized trade if the allocation hits 34.9% or 45.1%.

### 4. Building the "Location" Logic (Asset Location)

A truly tax-optimized rebalancer doesn't just look at what to buy, but where to put it. This requires your model to distinguish between Taxable Accounts (Brokerage) and Tax-Advantaged Accounts (IRA/401k).

| Asset Characteristic | Ideal Location | Reasoning |
| :--- | :--- | :--- |
| **High Dividend/Yield** | Tax-Advantaged | Avoids annual income tax drag. |
| **High Growth (No Div)** | Taxable | Benefits from lower Long-Term Cap Gains rates. |
| **High Turnover/Active** | Tax-Advantaged | Frequent trading doesn't trigger tax events. |

#### Understanding Asset Location

This table outlines **Asset Location**, a strategy designed to maximize after-tax returns by placing specific investments into account types that offer the most favorable tax treatment:

- **Tax-Advantaged Accounts (e.g., 401(k), IRA)**: These are best for assets that generate high levels of taxable income every year, such as **High Dividend** stocks or **Active/High Turnover** funds. By holding them here, you defer or avoid the immediate "tax drag" on those distributions.
- **Taxable Accounts (e.g., Standard Brokerage)**: These are ideal for **High Growth** assets that don't pay dividends. Because you aren't taxed until you sell, you can hold them for over a year to qualify for **Long-Term Capital Gains rates**, which are typically much lower than ordinary income rates.

### 5. Implementation: The Rebalance Algorithm

If you were writing the logic for this engine, the workflow would look like this:

1. **Identify Outliers**: Which asset classes are outside their tolerance bands?
2. **Harvest Losses**: Look across all asset classes for "underwater" lots to sell. This creates a **Tax Credit**.
3. **Fund Purchases**: Use the proceeds from loss-harvesting to buy the underweight asset classes.
4. **Rank Gains**: If more cash is needed, rank all remaining "overweight" lots by their tax impact per dollar and sell only the "cheapest" ones.

> ***Reporting Alpha***: The result of this engine is Tax Alpha—the extra return the client gets simply by being smart about taxes.