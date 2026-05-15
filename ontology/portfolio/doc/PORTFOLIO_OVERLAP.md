# Portfolio Overlap: The "Look-Through" Analysis

**Portfolio Overlap** occurs when an investor holds multiple investment funds (ETFs, Mutual Funds) that own the same underlying securities. While an investor might think they are diversifying by buying five different "Growth Funds," they may actually be doubling or tripling their exposure to a handful of mega-cap stocks.

## Why Overlap Matters

The primary goal of diversification is to spread risk. If your funds have high overlap, your diversification is an illusion.

- **Concentration Risk**: If Apple (AAPL) makes up 10% of Fund A and 12% of Fund B, and you own both in equal amounts, your total portfolio has an 11% concentration in one company. If that company underperforms, your entire portfolio suffers.

- **The "Hidden Bet"**: Overlap can lead to unintended sector bets. You might end up 40% invested in "Technology" without realizing it because every fund you own is chasing the same top-performing tech stocks.

- **Redundant Fees**: You are often paying multiple management fees (TER) to different fund managers to buy the exact same stocks.

## How to Calculate Overlap

There are two main ways to measure overlap:

### 1. Simple Security Overlap

This counts how many of the same companies appear in both funds.

> **Example**: If Fund A has 100 stocks and Fund B has 100 stocks, and 50 of those stocks are the same, the Security Overlap is 50%.


### 2. Weighted Overlap (The Professional Standard)

This is the more accurate measure. it takes the weight (percentage) of each shared holding and sums the minimum common weight.

**The Math**: For every shared stock, you take the lower of the two weights:

$$\text{Overlap \%} = \sum \min(\text{Weight in Fund A}, \text{Weight in Fund B})$$

### Scenario Example: Portfolio Overlap

| Stock | Weight in Fund A | Weight in Fund B | Common Weight (Min) |
| :--- | :--- | :--- | :--- |
| **Microsoft** | 8% | 5% | **5%** |
| **NVIDIA** | 4% | 10% | **4%** |
| **Tesla** | 3% | 0% | **0%** |
| **Total Overlap** | | | **9%** |

## Analyzing Overlap

To perform a "Look-Through" analysis, your system must aggregate the top_holdings or full portfolio disclosures of every fund in the portfolio.

### The Aggregation Process:

1. **Extract**: Pull the holdings and weights for all funds held in the portfolio.
2. **Normalize**: Scale the weights based on the size of the fund position relative to the total portfolio.
3. **Aggregate**: Group by Security Identifier (ISIN/Ticker).
4. **Identify**: Highlight the "Top Concentrated Positions" across the entire portfolio.

## Technical Implementation (JSON Logic)

```json
{
  "portfolio_id": "P-9921",
  "consolidated_holdings": [
    {
      "identifier": "AAPL",
      "name": "Apple Inc.",
      "total_weight": 0.085,
      "contributions": [
        { "fund_id": "ETF-1", "weight_contribution": 0.045 },
        { "fund_id": "ETF-2", "weight_contribution": 0.040 }
      ]
    },
    {
      "identifier": "MSFT",
      "name": "Microsoft Corp.",
      "total_weight": 0.072,
      "contributions": [
        { "fund_id": "ETF-1", "weight_contribution": 0.072 }
      ]
    }
  ],
  "overlap_alert": "HIGH"
}
```

### Summary Table: Overlap Impact

| Overlap % | Interpretation | Action Required |
| :--- | :--- | :--- |
| **0% - 20%** | Excellent Diversification | None. Funds are complementary. |
| **20% - 50%** | Moderate Overlap | Monitor for sector concentration. |
| **50% - 80%** | High Overlap | Significant redundancy; consider consolidating funds. |
| **80%+** | Extreme Overlap | You are likely holding two versions of the same index. |




