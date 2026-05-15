## Issuer

### Standard
**GLEIF**  
**ISO 17442 — Legal Entity Identifier (LEI)**

### What you get
- Legal entity domicile  
- Registered address country  
- Headquarters country  

### Used for
- Issuer country determination  
- Economic exposure analysis  
- Sanctions screening / KYC  
- Regulatory reporting  

### Example

issuer:
  lei: 5493001KJTIIGC8Y1R12
  country: CH

## Critical Modeling Rule

Financial instruments must never store legal identity, domicile, or country directly.

All such attributes are derived exclusively via:

***FinancialInstrument → Issuer → LEI***

### This guarantees:

- Consistent issuer country logic

- Correct exposure aggregation

- Clean sanctions and KYC processing

- Regulation-safe data models

## ISO 17442 — Legal Entity Identifier (LEI)

Overview

**ISO 17442** is the international standard that defines the Legal Entity Identifier (LEI) system.
It provides a globally consistent, regulated, and interoperable identifier for legal entities participating in financial transactions.

The standard is maintained by the International Organization for Standardization (ISO) and operationalized globally by the **Global Legal Entity Identifier Foundation (GLEIF)**.

### What ISO 17442 Defines

ISO 17442 specifies:

- The structure of an LEI (20 characters)

- Uniqueness and persistence requirements

- The governance model for issuance and maintenance

- The minimum reference data that must be publicly available

### LEI Structure (20 Characters)

An LEI has a fixed format:

- Characters 1–4: Local Operating Unit (LOU) prefix

- Characters 5–18: Entity-specific unique identifier

- Characters 19–20: Check digits (ISO 7064)

*Example: 5493001KJTIIGC8Y1R12*

### What Data an LEI Represents

ISO 17442 mandates two data layers.

#### Level 1 — “Who is who”

- Official legal name

- Legal form

- Registered address

- Headquarters address

- Country of domicile

#### Level 2 — “Who owns whom”

- Direct parent LEI

- Ultimate parent LEI

- Ownership relationship type (where applicable)

This enables legal entity identification and corporate hierarchy transparency.

### Why ISO 17442 Matters

ISO 17442 was introduced after the 2008 financial crisis to address a systemic issue:
the lack of a universal issuer identifier across markets and jurisdictions.

#### Today, LEI is:

- Mandatory under many regulations:
  - MiFID II
  - EMIR
  - Dodd-Frank
  - SFTR
  - FATCA
- Globally recognized (unlike national identifiers)
- Public and non-proprietary

### Typical Uses

- Issuer country and domicile determination
- Counterparty risk and exposure aggregation
- Sanctions and AML / KYC screening
- Regulatory and transaction reporting
- Cross-system data integration (trading, risk, reference data)

### Key Takeaway

ISO 17442 defines the LEI as the only globally standardized, regulated, and interoperable identifier for legal entities.

It is the authoritative reference for issuer identity in modern financial systems.

### Normalized Financial Ontology Model

####Modeling Principles

- Issuer is a first-class legal entity
- LEI is an identifier object, not embedded attributes
- Financial instruments reference the issuer, never duplicate issuer data

### Conceptual structure:

FinancialInstrument
  └── issued_by → Issuer
                     ├── has_identifier → LegalEntityIdentifier (LEI)
                     ├── has_legal_identity
                     └── has_corporate_hierarchy

## Instruments that always have an Issuer

### Equity Instruments

Ownership claims in a legal entity.

- Common shares (ordinary shares)
- Preferred shares
- Depositary receipts (ADR, GDR)
- Participation certificates
- Tracking stocks

Issuer:
Corporation or legal entity whose equity is represented.

### Debt Instruments

Contractual obligations to repay principal and interest.

- Bonds (government, corporate, municipal)
- Notes (MTN, commercial paper)
- Debentures
- Asset-backed securities (ABS, MBS)
- Covered bonds
-Loans (when securitized)

Issuer:
Borrower / obligor (sovereign, bank, corporation, SPV)

### Fund Instruments

Units or shares representing ownership in a collective investment vehicle.
- Mutual funds
- ETFs
- UCITS
- Hedge funds
- Closed-end funds
- Investment trusts

Issuer:
Fund vehicle (often an SICAV, unit trust, or similar legal structure)

### Derivative Instruments (Issued / OTC Form)

Contracts created by a counterparty or issuing institution.

- Warrants
- Certificates (participation, capital protection, yield enhancement)
- Structured notes
- OTC options
- OTC swaps
- Credit default swaps (CDS)

Issuer:
Typically a bank or financial institution (or counterparty in OTC)

### Structured Products

Hybrid instruments embedding derivatives into a note or certificate.

- Capital-protected notes
- Autocallables
- Reverse convertibles
- Equity-linked notes
- Index-linked notes

Issuer:
Usually an investment bank or structured-product issuer

### Insurance-Linked Securities

Capital market instruments transferring insurance risk.

- Catastrophe bonds
- Longevity bonds
- Insurance-linked notes (ILNs)

Issuer:
Insurance company or special purpose vehicle (SPV)

### Digital Securities / Tokenized Instruments

On-chain representations of traditional securities.

- Tokenized bonds
- Tokenized equity
- Security tokens

Issuer:
Underlying legal issuer remains mandatory

## Instruments That May Have an Issuer (Context-Dependent)

### Deposits & Cash-Like Instruments

- Term deposits
- Certificates of deposit (CDs)
- Structured deposits

Issuer:
Depositary bank

### Guarantees & Credit Enhancements

- Bank guarantees
- Letters of credit

Issuer:
Guaranteeing bank or institution

## Instruments That Do NOT Have an Issuer

These are important for contrast and correct modeling.

- Cash (physical currency in circulation)
- FX spot positions
- Commodities (gold, oil, wheat)
- Cryptocurrencies (Bitcoin, Ethereum)
- Indices (S&P 500, STOXX 50)
- Reference rates (LIBOR, SOFR)
- Exchange-traded derivatives (futures, listed options)

These instruments may have administrators, publishers, or exchanges, but no issuer in the legal sense.

### Modeling Rule (Canonical)

An instrument has an issuer if and only if there exists a legal entity that is contractually responsible for the rights or obligations embedded in that instrument.

In ontology terms:

- FinancialInstrument → hasIssuer → LegalEntity
- Cardinality:
  - 1..1 for equity, debt, funds, structured products
  - 0..1 or 0..n for derivatives (depending on OTC vs listed)
  - 0 for commodities, FX, indices, crypto
