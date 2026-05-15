# Issuance

In a Portfolio Management System (PMS) or an Investment Book of Record (IBOR), the ontology for issuance is the structural DNA that defines how a security is born and how it behaves throughout its life.

The system doesn't just see "a stock"; it sees a complex relationship between an **Issuer**, an **Instrument**, and the **Issuance Event**. Here is how that hierarchy is typically modeled:

## The Core Entities (The "Who" and "What")

The ontology begins by separating the entity that needs money from the contract used to get it.

- **Legal Entity (Issuer)**: The parent object. It contains metadata like the LEI (Legal Entity Identifier), country of domicile, credit rating, and industry sector.

- **Issuance (The Event)**: This is the specific instance of the instrument being released. A single company (Issuer) can have many issuances (e.g., Series A, Series B, or various bond tranches).

## The Issuance Metadata (The "Rules")

The PMS uses specific "slots" in the ontology to track how the issuance functions in the primary and secondary markets:

- **Identifiers**: This links the issuance to the world. It includes the **ISIN **(International), **CUSIP** (North America), and **SEDOL**.

- **Quantity & Par**: Total authorized shares/units versus the par value (the "face value" of the issuance).

- **Offering Price**: The "Book Price" set by the underwriter in the primary market.

- **Dates: \* Announcement Date**: When the market first hears about it.

  - **Dated Date**: When interest begins to accrue (for bonds).

  - **Issue Date**: The "Birthday" of the security.

## Relationships and Lifecycle

A sophisticated PMS ontology tracks how the issuance changes over time. This is often represented as a **State Machine**:

| State                    | Description |
|:-------------------------| :--- |
| **Pending / Proposed**   | The issuance is in the "roadshow" or underwriting phase. |
| **Active / Outstanding** | The security is trading in the secondary market. |
| **Corporate Action**     | The issuance is modified (e.g., a stock split or a bond "tap" where more units are issued). |
| **Matured / Redeemed**   | The issuance has reached its end of life (bonds) or been bought back. |

## Linkage to the Primary / Secondary Market

The ontology must distinguish between the **Issuance Account** (where the security originates) and the Trading Account (where it moves after the primary sale).

- **Primary Link**: The system links the issuance to the Underwriter Syndicate data, tracking fees and allocations.

- **Secondary Link**: The system links the issuance to Market Data Feeds (like Bloomberg or Refinitiv) to update the "Last Traded Price" from the secondary market.

## Why this matters for Portfolio Managers

If the ontology is poor, the system might treat a "New Issue" as a standard buy trade. If the ontology is correct, the system knows to:

- Apply different **tax logic** (Primary market purchases often have different stamp duties).

- Trigger **compliance checks** (e.g., "Are we exceeding our 10% limit on a single issuer?")

- Track **Settlement Lag** (Primary market settlements often take longer than the standard $T+2$ of the secondary market).

## Structure of an Issuance as a YAML example

In a professional Portfolio Management System (PMS), the YAML for an issuance needs to bridge the gap between the **Legal Entity** (who), the **Instrument Definition** (what), and the **Transaction Event** (how).

Here is a structured YAML representation of a Bond Issuance. This ontology separates the static "Master Data" from the "Issuance Event" details.

```yml
# Financial Instrument Issuance Ontology
issuance_record:
  id: "ISS-998877-AAPL-2026"
  status: "ACTIVE"  # Options: PROPOSED, BOOK_BUILDING, ACTIVE, MATURED, CANCELLED
  
  # 1. THE ISSUER (Legal Entity Master Data)
  issuer:
    name: "Apple Inc."
    lei: "HWUP0S0II8SBYYAH4222"
    domicile: "US"
    sector: "Technology"
    credit_rating:
      agency: "S&P"
      value: "AA+"
      last_updated: "2025-12-01"

  # 2. THE INSTRUMENT (Static Security Definition)
  instrument_details:
    type: "Fixed_Income_Bond"
    identifiers:
      isin: "US037833AS75"
      cusip: "037833AS7"
      ticker: "AAPL 4.5 2031"
    currency: "USD"
    tenor: "5Y"
    coupon_rate: 4.50  # Percentage
    frequency: "Semi-Annual"
    day_count_convention: "30/360"
    maturity_date: "2031-02-15"

  # 3. THE ISSUANCE EVENT (Primary Market Data)
  primary_market_event:
    issue_date: "2026-02-15"
    announcement_date: "2026-02-01"
    offering_price: 100.00  # Par value
    total_authorized_amount: 5000000000  # $5 Billion
    underwriting_syndicate:
      lead_manager: "Goldman Sachs"
      co_managers: ["JP Morgan", "Morgan Stanley"]
      underwriting_fee_bps: 35 # Basis points
    allocation_rules:
      retail_cap_percentage: 10
      institutional_priority: true

  # 4. SECONDARY MARKET LINKAGE (External Data Hooks)
  secondary_market_config:
    primary_exchange: "OTC"
    market_maker_ids: ["MM-CITI-01", "MM-VIRT-99"]
    liquidity_score: "HIGH"
    pricing_source: "BLOOMBERG_BVAL"
    
```

### Key Logic in this Ontology:

- **Normalization**: Notice that the issuer is a nested object. In a real database, this would be a foreign key to a "Legal Entity" table so that if Apple's credit rating changes, it updates across all 50 of their issuances simultaneously.

- **The "Status" State Machine**: The *status* field allows the PMS to hide the instrument from traders until it moves from BOOK_BUILDING to ACTIVE.

- **Basis Points (bps)**: In the primary market, fees are rarely expressed as percentages in the code to avoid floating-point errors; they are stored as integers representing basis points ($100 \text{ bps} = 1\%$).

- **Calculated Fields**: The *day_count_convention* is vital for the PMS to calculate "Accrued Interest" correctly when the bond starts trading in the secondary market.

## Primary and Secondary Market

In the world of finance, the distinction between primary and secondary markets is essentially the difference between **buying "new" vs. buying "used."**  The **primary market** is where securities are created and sold for the first time directly from the issuer to investors (think: a company raising money). The **secondary market** is where those same investors trade among themselves (think: the New York Stock Exchange).

Most major financial instruments exist in both ecosystems. Here are the primary types:

### Equities (Stocks)

This is the most common example. When a company "goes public," it enters the primary market. Once those shares are out in the wild, they live in the secondary market.

- **Primary Market**: Initial Public Offerings (IPOs) or Rights Issues. The money goes directly to the company to fund growth.

- **Secondary Market**: Trading on exchanges like the NASDAQ or NYSE. The money moves between investors; the company doesn't receive a dime from these trades.

### Debt Instruments (Bonds)

Governments and corporations use bonds to borrow money.

- **Primary Market**: When the U.S. Treasury or a corporation like Apple issues new bonds via an auction or underwriting.

- **Secondary Market**: Investors trade these bonds based on changing interest rates. If you want to sell a 10-year bond after holding it for only two years, you do so here.

### Money Market Instruments

These are short-term, highly liquid debt securities (usually maturing in less than a year).

- **Primary Market**: Direct issuance of Commercial Paper by corporations or Treasury Bills (T-Bills) by the government.

- **Secondary Market**: Highly active "over-the-counter" (OTC) markets where banks and institutional investors trade these instruments to manage daily liquidity.

### Derivatives

Derivatives are a bit unique because they are contracts rather than "assets" in the traditional sense, but they still follow this structure.

- **Primary Market**: The creation (writing) of a new option or futures contract.

- **Secondary Market**: Trading existing contracts on exchanges (like the CBOE) before they expire.

### Comparison Summary

| Feature | Primary Market | Secondary Market |
| :--- | :--- | :--- |
| **Purpose** | To raise capital for the issuer. | To provide liquidity for investors. |
| **Parties** | Issuer and Investor. | Investor and Investor. |
| **Price** | Usually fixed or determined by the issuer/underwriter. | Determined by supply and demand. |
| **Frequency** | Security is sold only once. | Security can be sold an infinite number of times. |

## How Pricing Works

In the primary market, the price is usually static and controlled. In the secondary market, it is dynamic and chaotic.

- **Primary Pricing**: For an IPO or a bond issuance, investment banks use a process called "book building." They look at institutional demand to set a fixed price (e.g., $22 per share). Investors either buy at that price or they don't.

- **Secondary Pricing**: Once the clock hits 9:30 AM on trading day, the "Underwriter" steps back. Now, the price is dictated by the Bid-Ask Spread. If more people want to buy than sell, the price climbs instantly. This is why you often see a "pop" in stock prices on their first day of trading.

## The Players Involved

The "who" changes significantly depending on which market you are entering.

- **Primary Market (The "Whales")**: This is often dominated by **Institutional Investors** — think hedge funds, pension funds, and insurance companies. While retail investors (regular people) can sometimes participate in IPOs through certain brokerages, the big "blocks" of shares are usually reserved for the big players.

- **Secondary Market (The "Public")**: This is the Great Equalizer. Anyone with a brokerage account (like Robinhood, Fidelity, or Schwab) can participate. Here, you aren't buying from the company; you’re buying from another person or a market maker.

## The Lifecycle of an Instrument

To visualize how a single financial instrument travels through these markets:

- **Issuance (Primary)**: A company needs \$100M to build a new factory. They issue 5 million shares at \$20 each.

- **The Handover**: The investment bank sells these shares to a group of mutual funds. The company gets its $100M (minus fees).

- **Trading (Secondary)**: One of those mutual funds decides they've made enough profit and sells 1,000 shares. You buy them at $25. The company is not involved in this transaction, but they watch the price because it reflects their "Market Cap."

### Why does this matter?

If you are looking for **stability**, you might look at primary market bonds (buying at par value). If you are looking for growth and liquidity, the secondary market is where you can enter and exit positions in seconds.

## The Underwriter

In the primary market, the **Underwriter** is the bridge between the company that needs money (the issuer) and the investors who have it. Usually, this role is played by large investment banks like Goldman Sachs, J.P. Morgan, or Morgan Stanley.

Think of an underwriter as a mix between a **high-stakes insurance agent** and a **marketing powerhouse**.

### The 3 Main Functions of an Underwriter

#### The "Safety Net" (Risk Assumption)

The most critical part of "underwriting" is the financial guarantee. In a Firm Commitment agreement, the underwriter actually buys the entire block of new shares or bonds from the company themselves.

- **The Goal**: They buy the shares at a slight discount (the "underwriting spread") and aim to sell them to the public at the full IPO price.

- **The Risk**: If the market hates the deal and the underwriter can't sell the shares, they are stuck holding them. They take the hit so the company doesn't have to.

#### Pricing and "Book Building"

The underwriter has to play Goldilocks: the price can't be too high (or no one buys) and it can't be too low (or the company leaves money on the table).

- They go on a **"Roadshow***, pitching the company to big institutional investors.

- They collect "indications of interest" to build a **"Book"**. This tells them exactly how much demand exists at various price points.

#### Regulation and Compliance

The underwriter acts as a gatekeeper. They conduct **Due Diligence**, which is a deep dive into the company’s books to ensure they aren't lying to the public. They also help file the S-1 Prospectus with regulators (like the SEC), which is the massive legal document that explains every risk associated with the investment.

#### Types of Underwriting Agreements

Not all deals are the same. The "flavor" of the contract determines who carries the most stress:

- **Firm Commitment**: The underwriter buys it all. Highest risk for the bank, most certainty for the company.

- **Best Efforts**: The bank doesn't buy the shares. They just promise to try their hardest to sell them. If they can't sell them all, the company just gets less money.

- **All-or-None (AON)**: If the underwriter can't sell the entire offering, the whole deal is canceled.

#### Why do companies pay them so much?

Underwriters usually charge a fee of 3% to 7% of the total money raised. It’s expensive, but companies pay it because:

- **Credibility**: Having a top-tier bank's name on your IPO tells the world you are a "real" company.

- **Network**: Most companies don't have the phone numbers of 500 hedge fund managers; underwriters do.

- During the first few days of a stock being in the secondary market, the underwriter often engages in **"Stabilization"**. If the price starts to crash, they are legally allowed to step in and buy shares to prevent a total collapse.

### Transition to Secondary Market

When the primary market "event" (the IPO or bond issuance) ends, the Underwriter hands the baton to the Market Makers. This transition is the bridge from the primary to the secondary market.

#### Part 1: How Market Makers "Take Over"

Once the Underwriter has finished selling the "new" shares at the fixed IPO price, the stock is listed on an exchange. At this exact moment, Market Makers (MMs) become the primary drivers of the stock's life.

- **The Handover**: On the morning of the IPO, the Underwriter provides the initial supply of shares to the exchange. The Market Maker then sets the "Opening Cross"—a massive matching of all buy and sell orders to find the first secondary market price.

- **Providing "Immediacy"**: In the secondary market, you don't want to wait hours for a buyer to show up. A Market Maker is obligated to always quote a buy price (Bid) and a sell price (Ask). They "take over" by using their own capital to buy when people want to sell and sell when people want to buy.

- **Stabilization**: For the first few days, the Underwriter and Market Maker often work together. If the price starts to plummet, the Underwriter (acting as a "Stabilizing Agent") might buy back shares to prevent a crash, while the Market Maker ensures the trading remains "orderly" (no massive gaps in price).

### Part 2: How Retail Investors get the "Book Price"

The "book price" is the official price set by the underwriter (e.g., $20.00). Historically, this was reserved for the "Whales" (Hedge Funds, Pensions), but today there are three main ways a retail investor can get it:

#### 1. "Indications of Interest" (Direct Allocation)

If your broker (e.g., Fidelity, Schwab, E*Trade, or SoFi) is part of the Underwriting Syndicate (the group of banks selling the shares), they may allow you to request an allocation.

- **The Process**: You submit an "Indication of Interest" (IOI) for a specific number of shares.

- **The Catch**: You usually need a high account balance (e.g., $100k-$250k) or be a "frequent trader." If the IPO is "hot," you might request 100 shares but only be granted 5.

#### 2. Fintech "IPO Access" Programs

Apps like Robinhood or SoFi have changed the game by negotiating with underwriters to take a small slice of the "book" specifically for their retail users.

- **How it works**: They offer a "lottery" or "first-come-first-served" system where users can buy shares at the exact same price as the big banks before the stock starts trading on the open market.

#### 3. The "Dutch Auction" (The Fairer Way)

Some companies (like Google did in 2004) bypass the traditional "underwriter's book" and use a **Dutch Auction**.

- **How it works**: Everyone (institutional and retail) submits a bid for how many shares they want and the maximum price they'll pay. The company starts at the highest price and works down until all shares are sold. Everyone then pays that final "clearing price".

#### The Risk of the "Book Price"

Getting the underwriter's price isn't always a win. If an IPO is "overpriced," the stock might open at $18.00 in the secondary market even though you paid $20.00 in the primary market. This is known as **"breaking the issue price"**.

### S-1 Prospectus

Reading an S-1 Prospectus can feel like trying to read a phone book written by lawyers. It’s often hundreds of pages long, but you don't need to read it cover-to-cover. Experienced investors look for specific "red flags" and data points to see if the Underwriter's price is actually a bargain or a trap.

Here is the "Cheat Sheet" for navigating an S-1 efficiently.

#### 1. The "Prospectus Summary" (The Pitch)

Found right at the beginning, this is the company’s "Elevator Pitch."

- **What to look for**: How do they actually make money? If you can’t explain their business model in two sentences after reading this, the company might be too complex or intentionally vague.

#### 2. "Risk Factors" (The Reality Check)

By law, the company must list everything that could possibly go wrong. This is the most honest section of the document because the company is protecting itself from future lawsuits.

- **The Filter**: Skip the generic stuff (e.g., "A global pandemic could hurt us").

- **The Red Flags**: Look for **concentration risks** (e.g., "One customer accounts for 40% of our revenue") or **legal risks** (e.g., "We are currently being sued for patent infringement").

#### 3. "Use of Proceeds" (The "Where is my money going?" section)

This tells you exactly what the company plans to do with the cash they raise in the Primary Market.

- **Good Sign**: Investing in R&D, building factories, or expanding into new markets.

- **Bad Sign**: Using the money primarily to pay off old debt or to pay out massive bonuses to early investors. You want your capital to fuel growth, not bail out the past.

#### 4. "Management’s Discussion and Analysis" (MD&A)

This is where the executives explain the financial numbers in plain English.

- **Look for Trends**: Are revenues growing? More importantly, are **margins** improving? If revenue is up but the cost to acquire customers is rising even faster, the business model might not be "scalable."

#### 5. "Selected Financial Data"

Look for the table comparing the last 3–5 years.

- **The "Bottom Line"**: Most IPO companies are not yet profitable (Net Loss). That’s okay, but look at the "Burn Rate"—how fast are they running through cash? If they only have 6 months of cash left, this IPO is a desperate survival move.

#### How to Find an S-1

All S-1s are public and free. You can find them on the SEC EDGAR database.

1. Go to SEC.gov.

2. Type in the company name.

3. Look for the filing type "S-1" or "S-1/A" (the /A means an amended version, which is usually the most recent).


#### Summary Checklist for a "Good" S-1 Filing

| Section | Checklist Item | What to Look For |
| :--- | :--- | :--- |
| **Prospectus Summary** | **Clarity & Mission** | Does it clearly define the problem the company solves and its unique value proposition? |
| **Risk Factors** | **Specificity** | Are the risks tailored to the business (e.g., specific regulatory hurdles) rather than just "boilerplate" legal warnings? |
| **Use of Proceeds** | **Capital Allocation** | Is there a clear plan for the funds (e.g., R&D, debt repayment, acquisitions) or is it vaguely for "general corporate purposes"? |
| **Management (MD&A)** | **Narrative Consistency** | Does management's explanation of financial trends align with the actual data in the financial tables? |
| **Financial Statements** | **Quality of Earnings** | Look for consistent revenue growth, manageable debt levels, and transparent accounting for one-time expenses. |
| **Governance** | **Board Composition** | Check for independent directors, diversity of expertise, and alignment of executive incentives with shareholder value. |
| **The "Equity Story"** | **Growth Levers** | Does the filing outline a believable path to long-term profitability and market expansion? |

### Hypothetical Examples

To understand how to "read between the lines" of an S-1, let's compare two hypothetical companies filing for an IPO. Both are tech startups, but their financials and disclosures tell very different stories.

#### Company A: "CloudScale" (The Healthy Growth Story)

**Summary**: Provides AI-driven logistics software for global shipping.

- **Use of Proceeds**: "60% for expanding our sales team in Europe and Asia; 40% for R&D to develop our automated warehouse module."
  - *Analysis*: **Green Flag**. They are using the primary market capital to capture more market share.

- **Risk Factors**: "We rely heavily on Amazon Web Services (AWS) for our infrastructure. A significant price hike from AWS could hurt our margins."
  - *Analysis*: **Standard/Manageable**. This is a common tech risk. It shows transparency without revealing a fatal flaw.

- **MD&A (Financials)**: Revenue grew 80% last year. Their "Cost of Revenue" only grew 30%.
  - *Analysis*: **Excellent**. This shows "operating leverage." As they get bigger, they become more profitable because their costs don't rise as fast as their sales.

- **Ownership**: The Founder/CEO still owns 35% of the company. 
  - *Analysis*: **Skin in the Game**. The person running the ship wins or loses along with you.

#### Company B: "BurnIt" (The Red Flag Special)

**Summary**: A luxury dog-walking app that offers "concierge canine experiences."

- **Use of Proceeds**: "70% to repay outstanding high-interest debt held by early venture capital investors; 30% for general corporate purposes."

- **Risk Factors**: "We are currently involved in a class-action lawsuit regarding the employment status of our walkers. If we lose, our business model may no longer be viable."
  - *Analysis*: **Danger**. This is an "existential risk." If this one thing goes wrong, the stock price could go to zero. 

- **MD&A (Financials)**: Revenue grew 100%, but their "Marketing Spend" grew 150%.
  - *Analysis*: **The "Leaky Bucket"**.They are buying their growth. They are spending \$1.50 in advertising just to make \$1.00 in sales. This is a business model that fails once the IPO cash runs out.

- **Ownership**: The Founders have already sold 90% of their shares to private equity firms.
  - *Analysis*: **The "Exit"**. The people who know the company best are trying to leave. Why should you be the one to buy in?

#### Summary of the Comparison

| Feature | CloudScale (Good) | BurnIt (Bad) |
| :--- | :--- | :--- |
| **Primary Goal** | Growth & Expansion | Debt Repayment / Exit |
| **Scalability** | Costs grow slower than sales | Costs grow faster than sales |
| **Insiders** | Buying or holding | Selling and leaving |
| **Legal** | Standard business risks | Business-ending litigation |

#### The "Underwriter's Price" Verdict

- **CloudScale**: You might be happy to pay the Underwriter's "book price" of \$25 because the fundamentals suggest the secondary market will drive it higher.

- **BurnIt**: Even if the Underwriter sets a "low" price of \$10, you might avoid it, knowing that the secondary market will likely sell off once the "hype" dies down.