# FIDLEG (FinSA in English)

**FIDLEG** (or **FinSA**Think of it as the Swiss version of the EU's **MiFID II**. Its main goal is to protect investors and create a level playing field for financial service providers (like banks and asset managers) in Switzerland. in English) stands for the Finanzdienstleistungsgesetz, the **Swiss Federal Act on Financial Services**. It officially went into effect on January 1, 2020.

Think of it as the Swiss version of the EU's **MiFID II**. Its main goal is to protect investors and create a level playing field for financial service providers (like banks and asset managers) in Switzerland.

Here is a breakdown of how it works and why it matters:

## 1. Client Segmentation (The "Protection Ladder")

FIDLEG requires financial institutions to sort their clients into three categories. Your category determines how much protection and information you are legally entitled to receive.

### MiFID II Client Classification and Protection Levels

FIDLEG requires financial institutions to sort their clients into three categories. Your category determines how much protection and information you are legally entitled to receive.

| Category | Who they are | Level of Protection |
| :--- | :--- | :--- |
| **Retail Clients** | Private individuals, families, and small businesses. | **Highest** (Most transparency, strict rules). |
| **Professional Clients** | Large companies, public entities, and wealthy individuals (HNWIs) who "opt-out." | **Medium** (Assumed to have more knowledge). |
| **Institutional Clients** | National banks, insurance companies, and large financial intermediaries. | **Lowest** (They are experts; few conduct rules apply). |


## 2. Rules of Conduct (How they must treat you)

If you are a retail client, your bank or advisor must follow specific steps before they can sell you anything:

- **Duty to Inform**: They must explain who they are, what services they offer, the risks involved, and any costs or fees.

- **Suitability & Appropriateness Tests: Appropriateness**: If they suggest a single trade, they must check if you have the knowledge to understand it.
  - **Suitability**: If they manage your whole portfolio, they must check your financial situation and investment goals to ensure the strategy fits your life.

- **Best Execution**: They are legally required to execute your orders in a way that gets you the best possible result (considering price, speed, and quality).

- **Documentation**: They must keep records of what was discussed and why certain recommendations were made.

## 3. Transparency on Products

FIDLEG introduced the **Key Information Document (KID)** or Basisinformationsblatt (BIB). This is a short, easy-to-read "cheat sheet" (usually 2-3 pages) that explains:

- What the product is.

- The risk/reward profile (on a scale of 1 to 7).

- The exact costs and how they affect your return.

- What happens if the provider goes bust.

## 4. Why was it created?

Before FIDLEG, Swiss financial law was a bit of a "patchwork quilt." Different rules applied depending on whether you were talking to a bank, an insurance company, or an independent asset manager.

### FIDLEG fixed this by:

1. **Standardizing rules** across the entire industry.
2. **Increasing transparency** regarding "retrocessions" (kickbacks/commissions) to prevent conflicts of interest.
3. **Strengthening** legal standing for clients, making it easier and cheaper to resolve disputes through an Ombudsman.

### Comparison at a Glance: FIDLEG vs. MiFID II

While they are very similar, FIDLEG is generally seen as slightly more "principles-based" and flexible compared to the highly prescriptive EU MiFID II rules, though both share the same DNA of protecting the end investor.

## Implementation and Integration

In the world of Swiss wealth management, FIDLEG (FinSA) is not just a legal checklist; it’s a "digital guardrail" integrated directly into the software that relationship managers (RMs) and portfolio managers use every day.

When you use a Portfolio Management System (PMS) or an Advisory Tool (like Avaloq, Finnova, or specialized SaaS like WealthArc), FIDLEG is implemented through several automated modules:

### 1. The Digital Onboarding Funnel (CRM)

The process starts in the CRM, where the software forces the RM to complete specific steps before an account can even be activated

- **Automated Segmentation**: Based on the client's assets and entity type, the tool automatically tags them as Retail, Professional, or Institutional.

- **Opt-in/Opt-out Workflows**: If a wealthy client wants to "opt-out" to be treated as a Professional (allowing them to buy riskier products), the system triggers a digital signature workflow and stores the mandatory proof of "knowledge and experience."

### 2. The "Hard Block" Pre-Trade Check

This is the most critical implementation. When an advisor tries to place an order, the tool runs a Pre-Trade Compliance Check in real-time:

- **The "Yellow Light" (Warning)**: If a product is "inappropriate" (e.g., a complex derivative for a client who doesn't understand them), the system pops up a warning. The advisor can often override this but must document the reason.

- **The "Red Light" (Block)**: If a product is "unsuitable" (e.g., it exceeds the client's maximum risk score or doesn't match their investment horizon), the system will literally disable the "Execute" button.

- **KYP (Know Your Product)**: The tool cross-references the trade with a centralized database (like SIX or Bloomberg) to ensure the mandatory **Key Information Document (KID)** is available and has been provided to the client.

### 3. Portfolio Monitoring & "Passive Breaches"

For portfolio management (discretionary mandates), the software monitors the entire account 24/7:

- **Drift Alerts**: If market movements cause a stock to grow so much that the portfolio now exceeds the client's "Risk Ability," the system flags a Passive Breach.

- **Rebalancing Engines**: Modern advisory tools have "Rebalance" buttons that automatically calculate the trades needed to bring the portfolio back into FIDLEG compliance.

### 4. The Audit Trail (Record Keeping)

FIDLEG requires firms to prove why they gave certain advice. Portfolio management solutions automate this by:

- **Freezing Notes**: Once an investment proposal is sent, the rationale and the state of the portfolio at that moment are "frozen" in a non-editable log.

- **Automated Reporting**: Every year, the system can automatically generate a "Suitability Report" for the client, detailing how the investments still align with their goals.

### Summary of the Digital Workflow

**Onboarding** (Segmentation) $\rightarrow$ **Profiling** (Suitability Test) $\rightarrow$ **Investment Strategy** (Constraints) $\rightarrow$ **Order Entry** (Pre-trade check) $\rightarrow$ **Execution** (Best Execution Log) $\rightarrow$ **Monitoring** (Post-trade check).

## What FIDLEG cares about

While FIDLEG is obsessed with **risk** and **transparency**, it doesn't actually legally mandate that a bank achieves a certain return or even tracks performance in a specific way. However, it is indirectly connected through the "Duty to Report."

### 1. What FIDLEG doesn't care about

FIDLEG is "process-oriented," not "result-oriented." The regulator (FINMA) doesn't care if a portfolio loses 20%, as long as:

- The client was **warned** about the risk.

- The risk was **suitable** for the client’s profile.

- The bank followed the **Best Execution** rules.

### 2. What FIDLEG does require (The Reporting Duty)

Under **Article 18 of FIDLEG**, there is a "Duty to render account." This means the provider must provide a report to the client that includes:

- **The agreed services**: What did we say we would do?

- **The composition of the portfolio**: What do you own?

- **The costs**: How much did we charge you?

**Crucially**: While most banks include "Performance" in these reports because clients demand it, FIDLEG itself focuses more on the costs and holdings than the percentage of gain or loss.

### 3. Performance is usually handled by other standards

While FIDLEG doesn't dictate performance monitoring, other frameworks do:

- **GIPS (Global Investment Performance Standards)**: This is the "gold standard" for how performance should be calculated (to prevent banks from "cherry-picking" good months to look better).

- **Contract Law**: If a portfolio manager deviates significantly from the agreed strategy (e.g., buying high-risk tech stocks for a "Conservative" client), the performance becomes evidence of a Suitability Breach under FIDLEG.

### Why this matters software/tools

- **Compliance Module**: Checks if you can buy the stock (FIDLEG).

- **Performance Module**: Checks how much money the stock made (Commercial/Client Service).

If a tool says it is "FIDLEG compliant," it usually means it handles the **Suitability, Documentation, and Transparency** requirements, not necessarily the IRR or TWR calculations.

