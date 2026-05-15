# Markets in Financial Instruments Directive - MIFID

MiFID (Markets in Financial Instruments Directive) is the cornerstone of European financial services regulation. It was designed to increase transparency across the European Union's financial markets and standardize the regulatory disclosures required for particular operations.

Since its original inception in 2007, it has evolved into MiFID II (implemented in 2018), which significantly expanded the scope to include more asset classes and stricter reporting requirements.

## What MiFID Does

At its core, MiFID aims to create a single market for investment services and activities. It ensures that whether you are investing in Paris, Berlin, or Dublin, you are protected by the same set of high-level rules.

### 1. Investor Protection

MiFID forces firms to act in the best interest of their clients. This includes:

- **Suitability and Appropriateness**: Firms must assess a client's knowledge, experience, and financial situation before recommending products.

- **Best Execution**: Investment firms are legally required to take all sufficient steps to obtain the best possible result for their clients when executing orders (considering price, cost, speed, and likelihood of execution).

- **Inducements**: It limits the "kickbacks" or commissions that investment advisors can receive from product providers, reducing conflicts of interest.

### 2. Market Transparency

MiFID II moved more trading onto regulated platforms.

- **Pre-trade transparency**: Venues must publish the prices and depth of trading interest (the "order book").

- **Post-trade transparency**: Firms must publish the price, volume, and time of executed trades as close to real-time as possible.

### 3. The "Passporting" System

This is one of the most critical features for the industry. A financial firm authorized in one EU member state can provide its services to customers in any other member state without needing further authorization from that country's local regulator.

## How it Works: Key Mechanisms

The regulation operates through several layers of classification and reporting:

### Client Classification

To ensure people get the right level of protection, MiFID categorizes clients into three groups:

1. **Retail Clients**: Receive the highest level of protection (e.g., everyday individual investors).
2. **Professional Clients**: Entities or individuals with enough experience to be presumed capable of making their own investment decisions.
3. **Eligible Counterparties**: Typically large institutions (like banks) that receive the lowest level of protection because they are market experts.

### Transaction Reporting

Every time a trade happens, a massive amount of data is sent to regulators. This helps authorities spot **market abuse**, such as insider trading or market manipulation, by seeing exactly who traded what, when, and for how much.

### Unbundling of Research

Before MiFID II, investment banks often gave "free" investment research to asset managers in exchange for the asset manager directing trades through that bank. MiFID II forced these to be "unbundled," meaning asset managers now have to pay for research separately. This ensures that trades are made because the execution is good, not because the research was "free."

### Summary Table

| Feature | Goal |
| :--- | :--- |
| **Best Execution** | Ensure clients get the best price/speed for their trades. |
| **Transaction Reporting** | Give regulators the data needed to stop market manipulation. |
| **Product Governance** | Ensure complex products are only sold to people who understand them. |
| **Transparency** | Ensure the public can see what is being traded and at what price. |

## Impact on the Valuation and Risk of Securities

MiFID II doesn't just regulate how people talk to each other; it fundamentally changes the "math" and logic behind how financial instruments are valued, priced, and risk-managed. If you are a quantitative modeler or a risk manager, MiFID II effectively forces you to move from "theoretical" or "opaque" models to data-driven, auditable frameworks.

### 1. Valuation: From Model-Based to Market-Based

Before MiFID II, many illiquid instruments (like certain corporate bonds or complex derivatives) were valued using "Mark-to-Model" approaches, often relying on internal assumptions. MiFID II’s transparency requirements have forced a shift.

- **The "Liquid" vs. "Illiquid" Filter**: Regulators (ESMA) now run quantitative tests to determine if an instrument is "liquid." If your model treats a bond as illiquid but the regulator marks it as liquid, you are forced to provide firm quotes and near real-time pricing.

- **Consolidated Tape Data**: Models now have access to a much larger pool of post-trade data (the price and volume of every trade across the EU). Quantitative analysts use this data to calibrate **Yield Curves** and **Volatility Surfaces** with actual market evidence rather than just "indicative" quotes from brokers.


### 2. Best Execution Modeling

"Best Execution" is no longer a "best effort" policy; it is a measurable requirement.

- **TCA (Transaction Cost Analysis)**: Firms must now build or buy complex models to prove they got the best price. This involves modeling the Market Impact—how much your own trade moved the price—and comparing your execution against a Benchmark (like VWAP: Volume-Weighted Average Price).

- **Venue Selection Models**: Smart Order Routers (SORs) use algorithms to model which "venue" (stock exchange vs. private dark pool) has the highest probability of filling an order at the best price.

### 3. Algorithmic Trading & Model Governance

If you use a computer to determine any parameter of an order (price, timing, or quantity), you are "algorithmic trading" under MiFID II. This triggers strict Model Governance:

- **Testing and Sandboxing**: You cannot just "go live" with a new pricing model. It must be tested in a non-live environment to ensure it doesn't contribute to "disorderly trading" (e.g., flash crashes).

- **Kill Switches**: Every model must have a "kill functionality" that can be manually or automatically triggered if the model starts behaving erratically.

- **Stress Testing**: You are required to run annual stress tests on your trading algorithms to prove they can handle extreme market volatility.

### 4. Impact on Quantitative Research (Unbundling)

One of the most technical shifts happened in how research is "priced."

- **The Research Valuation Model**: Historically, research was "free" (bundled with commissions). Now, firms must put a hard dollar value on it. This has led to the creation of models that track the Alpha (excess return) generated by specific analyst reports to decide if the research is worth the fee.

### Comparison: Modeling Before vs. After MiFID II

| Feature | Pre-MiFID II Modeling | Post-MiFID II Modeling |
| :--- | :--- | :--- |
| **Data Source** | Small, proprietary datasets. | Large, public "Consolidated Tape" data. |
| **Pricing** | Often "Mark-to-Model" (internal). | Heavily "Mark-to-Market" (external). |
| **Algo Risk** | Focus on P&L and basic limits. | Focus on "Market Integrity" and stress tests. |
| **Transparency** | Models kept "black box." | Models must be auditable by regulators. |