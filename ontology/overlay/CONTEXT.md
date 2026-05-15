# Financial Overlays

In financial modeling and portfolio management, an overlay is a strategy where a new layer of risk or asset exposure is applied on top of an existing portfolio without disturbing the underlying assets.

Think of it like a transparent sheet placed over a map: the original map (your core investments) stays exactly where it is, but the sheet adds new markings (hedges or enhancements) that change the overall picture.

## How Overlays Work

Overlays are typically executed using **derivatives** (like futures, options, or swaps). Because these instruments are capital-efficient—meaning they require very little upfront cash (margin) compared to the total value they control—you can change the behavior of a portfolio without selling your stocks or bonds.

### Common Types of Overlays

- **Currency Overlay**: If you own international stocks, you are exposed to currency fluctuations. An overlay manager uses FX forwards to "cancel out" the currency risk or to bet on specific exchange rates, leaving the underlying stock picks untouched.
- **Rebalancing Overlay**: Large institutional funds often drift away from their target allocations (e.g., 60% stocks / 40% bonds) as markets move. Instead of selling physical assets—which incurs high transaction costs and taxes—they use futures to "nudge" the exposure back to the target.
- **Tactical Asset Allocation (TAA)**: If a model suggests a short-term opportunity in gold, an overlay can add gold exposure to a standard portfolio for a few months and then remove it easily once the opportunity passes.
- **Risk Overlay (Hedging)**: Using put options to protect a portfolio against a market crash. The "overlay" acts as an insurance policy that sits on top of the long-term holdings.

### There are many more types of overlays:
- **Interest Rate Overlay**: If you're invested in bonds, you might want to protect against rising interest rates. An overlay manager can use interest rate swaps or caps to lock in current yields or cap future increases.
- **Market Neutral Overlay**: This strategy aims to eliminate market direction risk by taking long and short positions in different assets or sectors. It's like having a balanced diet where you eat both fruits and vegetables, but also include some protein.
- **Volatility Overlay**: If you're concerned about market volatility, you can use options to hedge against sudden drops. This is like having an umbrella ready for rain, but not necessarily for every day.
- **Sector Rotation Overlay**: If you believe certain sectors will outperform others, you can use overlays to rotate your portfolio dynamically. It's like changing your wardrobe based on the weather forecast.
- **Commodity Overlay**: If you're invested in equities, you might want to diversify into commodities like oil or gold. An overlay manager can use futures contracts to gain exposure to these assets without committing to physical delivery.
- **Credit Overlay**: If you're invested in high-yield bonds, you might want to protect against default risk. An overlay manager can use credit default swaps to insure against potential losses.
- **Event-Driven Overlay**: If you're invested in a company that's facing a major event (like a merger or acquisition), you can use overlays to capitalize on the expected price movement. It's like betting on a horse race, but with stocks.


## Why Use an Overlay?

| Feature | Physical Trading | Overlay Strategy |
| :--- | :--- | :--- |
| **Speed** | Slow (settlement takes days) | Instant (derivatives trade in seconds) |
| **Cost** | High (commissions, spreads, taxes) | Low (minimal transaction costs) |
| **Disruption** | High (must fire/hire managers) | Low (underlying managers keep working) |
| **Capital** | Requires 100% of the cash | Uses leverage/margin |

## The Modeling Perspective

When modeling these instruments, you treat the overlay as a **synthetic position**. In a spreadsheet or risk engine, the total portfolio return $R_p$ is modeled as:

$$
R_p = \sum_{i=1}^{n} (w_i \cdot r_i) + \frac{\Delta_{deriv}}{Value_{port}}
$$

Where the first part represents the physical assets and the second part represents the "notional" gain or loss from the overlay derivatives.

> **A Note of Caution**: Because overlays often use leverage, they can introduce "basis risk"—the risk that the derivative doesn't perfectly track the asset it's supposed to hedge.

## Example Currency Overlay

To illustrate how this works, let's look at a **Currency Overlay**The Scenario. This is one of the most common applications because it cleanly separates the skill of picking stocks from the volatility of foreign exchange markets.

### The Scenario

Imagine you are a US-based investor who puts $1,000,000 into the Japanese stock market (the Nikkei 225).

1. **The Good News**: The Japanese stocks perform brilliantly and go up **10%**.
2. **The Bad News**: During that same period, the Japanese Yen (JPY) weakens against the US Dollar (USD) by **10%**.

Without an overlay, your total return is roughly **0%**. The gain in the stocks was completely wiped out by the loss in the currency conversion.

### The Overlay Solution

To fix this, you apply a **Short JPY / Long USD** overlay using forward contracts. This "locks in" the exchange rate.

| Component | Performance (Local) | Impact on USD |
| :--- | :--- | :--- |
| **Physical Assets** (Japanese Stocks) | +10% | $0 (Wiped out by FX) |
| **Overlay** (Short JPY Forward) | +10% | +$100,000 |
| **Total Portfolio Result** | | **+$100,000 (10%)** |

By using the overlay, you successfully "captured" the stock market's growth and "neutralized" the currency risk.

### Modeling the Math

In a financial model, we look at the Net Exposure. If $S$ is the spot exchange rate and $F$ is the forward rate used in the overlay, the hedged return ($R_h$) is modeled as:

$$
R_h = (1 + R_{asset})(1 + e) + H(F/S - (1 + e))
$$

Where:
- $R_{asset}$ is the return of the underlying stocks.
- $e$ is the change in the exchange rate.
- $H$ is the Hedge Ratio (usually 1.0 for a full hedge).

### Key Modeling Considerations

- **Cash Flow Management**: Overlays generate "variation margin." If your overlay is winning, you get cash; if it's losing, you must post cash. A model must account for having enough liquidity to support these margin calls without selling the underlying stocks.
- **Roll Yield**: Forward contracts expire. Modeling must include the cost (or benefit) of "rolling" the contract forward every 30 or 90 days.

## Key Modeling Considerations

To build a robust financial model for overlays, you need an ontology that treats the **Overlay** as a distinct entity that interacts with, but remains separate from, the **Base Portfolio**. This separation is crucial because it allows us to isolate the performance of the overlay from the base portfolio, ensuring that any performance attributed to the overlay is not influenced by the base portfolio's performance.

In an ontology, we define the "Is-A" (hierarchy) and "Has-A" (relationship) properties. Here is a draft structure for an **Overlay Management Ontology (OMO)**.

### 1. Core Classes (Entities)

- $BasePortfolio$: The underlying "physical" assets (e.g., Equities, Fixed Income).
  - *Attributes*: Market Value, Currency, Tax Lot ID.
- $OverlayProgram$: The strategic layer applied to the portfolio.
 - *Sub-classes*: $CurrencyOverlay, RebalancingOverlay, YieldEnhancement, TailRiskHedge$.
- $Instrument$: The tools used to execute the overlay.
 - *Sub-classes*: $FuturesContract, FXForward, TotalReturnSwap, Option$.
- $PolicyConstraint$: The rules governing the overlay. 
 - *Sub-classes*: $HedgeRatio, TrackingErrorLimit, MarginThreshold$.

### 2. Relationship Schema (Properties)

| Domain (Source)    | Relationship | Range (Target)      | Logic |
|:-------------------| :--- |:--------------------| :--- |
| $OverlayProgram$   | targets | $BasePortfolio$     | Defines which assets the overlay is "covering." |
| $OverlayProgram$   | implemented_via | $Instrument$        | Links the strategy to the derivative contracts. |
| $Instrument$       | requires | $CollateralAccount$ | Tracks the cash/margin needed to support the overlay. |
| $PolicyConstraint$ | limits | $OverlayProgram$    | Ensures the overlay doesn't exceed risk mandates. |
| $MarketData$       | triggers | $RebalancingEvent$   | When the gap between "Actual" and "Target" exceeds a threshold. |

### 3. The Logic Flow (Triples)

In a semantic model, the data flow looks like this:

1. **Selection**: BasePortfolio (Japanese Equities) $\xrightarrow{has\_exposure\_to}$ Currency (JPY).
2. **Definition**: CurrencyOverlay $\xrightarrow{is\_subclass\_of}$ OverlayProgram.
3. **Action**: CurrencyOverlay $\xrightarrow{offsets}$ JPY_Exposure.
4. **Execution**: CurrencyOverlay $\xrightarrow{executes}$ FXForward (Short JPY/Long USD).
5. **Monitoring**: FXForward $\xrightarrow{impacts}$ TotalPortfolioReturn (Synthetically).

### 4. Modeling the "Synthetic" Nature

In your financial model, the ontology must account for the Notional Value. Unlike a physical stock where $Quantity \times Price = Value$, an overlay has:

- **Notional Exposure**: The amount of the market you are controlling (e.g., $1M).
- **Market Value**: Often near zero at inception (for forwards/swaps).
- **Variation Margin**: The actual cash moving in/out daily.

**Ontology Note**: Ensure your model distinguishes between **Economic Exposure** (Physical + Overlay) and **Cash Exposure** (Physical only).

### 5. Visualizing the Ontology Architecture

@startuml
skinparam handwritten false
skinparam monochrome true
skinparam packageStyle rectangle
skinparam shadowing false

title Financial Overlay Ontology Model

package "Physical Layer" {
    entity "Investment Universe" as A
    entity "Base Portfolio" as B
    entity "Equity/Bond Holdings" as C
}

package "Management Layer" {
    entity "Overlay Manager" as D
    entity "Overlay Strategy" as E
    entity "Currency Hedge" as F
    entity "Tactical Rebalance" as G
}

package "Synthetic Layer" {
    entity "Derivatives Layer" as H
    entity "Futures/Forwards/Options" as I
    entity "Collateral/Cash Buffer" as J
}

' Relationships
A --> B : defines
B --> C : contains

D --> E : manages
E --> F : implements
E --> G : implements

F ..> C : <<offsets risk>>
G ..> C : <<adjusts weight>>

E --> H : utilizes
H --> I : consists of

I -- J : requires
J -- B : encumbers / supports

note right of J
  Margin requirements and 
  liquidity management
end note

@endum