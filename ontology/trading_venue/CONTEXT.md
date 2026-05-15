# Trading Venues

## Overview

The **Market Identifier Code (MIC)** is a standardized code used to uniquely identify **trading venues** and **market segments** worldwide.  
MICs are defined by **ISO 10383** and maintained under the authority of the **:contentReference[oaicite:0]{index=0} (ISO)**.

Each MIC precisely identifies **where a financial instrument is traded**, independent of the instrument itself.

## Standard

- **ISO Standard**: ISO 10383  
- **Name**: Market Identifier Codes (MIC)  
- **Authority**: ISO  
- **Scope**: Global  
- **Update frequency**: Ongoing (additions, changes, deprecations)

## What the MIC Identifies

A MIC represents **one of the following**:

1. **Operating Market / Trading Venue**  
   Examples:
   - Regulated markets
   - Multilateral Trading Facilities (MTF)
   - Organised Trading Facilities (OTF)
   - Exchanges

2. **Market Segment** (optional, secondary MIC)  
   Used to distinguish:
   - Equity vs derivatives segments  
   - Lit vs dark order books  
   - Auction vs continuous trading

A complete trading reference may therefore include:
- One **operating MIC**
- One **segment MIC**


## What You Get From MIC Data

Using MIC codes allows systems to reliably determine:

- Exact **trading venue**
- **Country** of execution
- **Regulatory classification** of the venue
- **Market structure** (exchange, MTF, OTF, internalizer)
- Eligibility for **regulatory regimes** (MiFID II, EMIR, etc.)


## Typical Use Cases

### Regulatory & Compliance
- MiFID II transaction reporting
- Best execution obligations
- Market transparency and surveillance
- Trade and transaction reporting

### Trading & Execution
- Routing orders to the correct venue
- Distinguishing primary vs secondary listings
- Liquidity and venue analysis

### Market Data
- Entitlement checks
- Venue-specific price feeds
- Consolidated tape construction

## Canonical Modeling Guidance

In a financial data ontology, **MIC is a property of the trading venue**, not of the instrument itself.

Typical placement:
- `TradingVenue`
- `Listing`
- `ExecutionVenue`

It should **not** be embedded directly into:
- Issuer
- Financial instrument definition


## Example

```yaml
trading_venue:
  mic: XSWX
  name: SIX Swiss Exchange
  country: CH
  venue_type: regulated_market
