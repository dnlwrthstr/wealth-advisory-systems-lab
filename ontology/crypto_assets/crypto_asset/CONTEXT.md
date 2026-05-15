# Crypto Assets (Digital Assets) in a Portfolio Context

A **Crypto Asset** is a digital representation of value or rights that uses cryptography for security and is typically recorded on a distributed ledger (Blockchain). Unlike traditional currencies or securities, crypto assets operate without a central intermediary like a bank or government.

## Common Types of Crypto Assets

| Type | Description | Example |
| :--- | :--- | :--- |
| **Payment Coins** | Digital "cash" designed for peer-to-peer transactions. | Bitcoin (BTC), Litecoin (LTC) |
| **Smart Contract Platforms** | Programmable blockchains that host decentralized apps (dApps). | Ethereum (ETH), Solana (SOL) |
| **Stablecoins** | Tokens pegged to a stable asset like the US Dollar or Gold. | USDC, USDT, DAI |
| **Utility Tokens** | Provide access to a specific product or service on a network. | Chainlink (LINK), Filecoin (FIL) |
| **Governance Tokens** | Grant voting rights in a Decentralized Autonomous Organization (DAO). | Uniswap (UNI), Aave (AAVE) |

## How Crypto Assets Work

Crypto assets differ from "paper" assets because they are **bearer instruments** in digital form. If you hold the "Private Keys," you own the asset.

- **Decentralization**: Transactions are verified by a network of computers (nodes) rather than a central clearinghouse.
- **Blockchain**: A public, immutable ledger that records every transaction in the history of the asset.
- **Wallets**: Digital interfaces used to store keys and interact with the blockchain
  - **Hot Wallet**: Connected to the internet (faster, but higher risk)
  - **Cold Wallet**: Offline storage (slower, but highly secure).

## Why Include Crypto in a Portfolio?

1. **Asymmetric Returns**: Historically, crypto has shown the potential for high growth compared to traditional asset classes.
2. **Portfolio Diversification**: Crypto often has a low correlation with stocks and bonds, though this "decoupling" varies during global liquidity shifts.
3. **Digital Gold**: Bitcoin is frequently viewed as a "store of value" due to its hard-coded scarcity (only 21 million will ever exist).

## Key Values for Modeling a Crypto Asset

To model a crypto position accurately in a financial system, you need data points that bridge the gap between "Traditional Finance" (TradFi) and "Decentralized Finance" (DeFi).

### 1. Identity & Network

- **Symbol/Ticker**: The short code (e.g., BTC, ETH).
- **Native Blockchain**: The network it lives on (e.g., Ethereum, Bitcoin, Polygon).
- **Contract Address**: For tokens (like ERC-20), the specific code address on the blockchain to ensure it isn't a "fake" or "impersonator" token.

### 2. Supply Metrics

- **Circulating Supply**: The number of coins currently in the hands of the public.
- **Total/Max Supply**: The absolute limit of coins that can ever be created.
- Market Cap: $(\text{Price} \times \text{Circulating Supply})$.

## Risks of Crypto Assets

### Volatility Risk

Crypto prices can fluctuate 10%–20% in a single day. This makes them high-risk for short-term liquidity needs.

### Regulatory Risk

Governments may change the legal status of crypto assets, tax them aggressively, or ban certain types of "Privacy Coins."

### Security (Custody) Risk

If a private key is lost or stolen, the assets are gone forever. There is no "forgot password" button on a decentralized blockchain.

### Smart Contract Risk

For tokens and DeFi platforms, a bug in the underlying code can lead to a "hack" or loss of funds.

### Technical Data Model (JSON Example)

In a wealth management API, a crypto position requires the address and network to verify the valuation.

```json
{
  "instrument_id": "BTC-BITCOIN-MAINNET",
  "instrument_name": "Bitcoin",
  "type": "CRYPTO_ASSET",
  "sub_type": "COIN",
  "network": "BITCOIN",
  "ticker": "BTC",
  "price_usd": 68500.00,
  "custody_type": "COLD_STORAGE",
  "wallet_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
  "is_stakable": false
}
```

## Is a crypto asset a security?

In the financial world, the question of whether a **Crypto Asset** is a **Security** is one of the most significant legal and technical debates of the decade.

When you model crypto "as a security," you are shifting from treating it as a digital currency (like cash) to treating it as an investment contract (like a stock). This change triggers a massive shift in the data attributes required for compliance, reporting, and valuation.

### The "Security" Test (The Howey Test)

In many jurisdictions, a digital asset is classified as a security if it meets four criteria:

1. It is an **investment of money**.
2. In a **common enterprise**.
3. With an expectation of profit.
4. Derived from the efforts of others (e.g., a development team or foundation).

**The General Rule**: Bitcoin is widely viewed as a Commodity (like Gold), while many ICO tokens (Initial Coin Offerings) are viewed as Securities because they rely on a central team to build value.

## Modeling Crypto as a Security: Required Attributes

If an asset is classified as a security, your data model must expand beyond simple wallet addresses to include regulatory and corporate metadata.

### 1. Regulatory Identification

- **ISIN/CUSIP**: Unlike native coins, "Security Tokens" often receive a standard International Securities Identification Number.

- **Registration Status**: Whether the asset is registered with a regulator (e.g., SEC in the US, FINMA in Switzerland).

- **Restricted Person List**: A list of who cannot hold the asset (e.g., US citizens for certain offshore tokens).

### 2. Corporate Governance

Since securities imply an "enterprise," you must model the rights associated with the token:

- **Voting Rights**: Does the token allow the holder to vote on corporate actions?
- **Dividend/Distribution Rights**: Does the token pay out a portion of the project’s revenue?
- **Liquidation Preference**: Where does the token holder stand if the project fails?

### 3. Compliance & KYC (Know Your Customer)

Security tokens often have "Programmable Compliance" built into the smart contract:

- **Whitelist Status**: The token cannot be transferred to a wallet that hasn't passed identity verification.
- **Transfer Restrictions**: Rules that prevent the asset from being sold for a specific "lock-up" period (e.g., Rule 144 in the US).

#### Comparison: Native Coin vs. Security Token

| Feature | Crypto as "Currency/Commodity" | Crypto as "Security" |
| :--- | :--- | :--- |
| **Example** | Bitcoin (BTC) | Real Estate Token / Equity Token |
| **Primary ID** | Ticker / Network Address | ISIN / Ticker |
| **Valuation** | Supply/Demand on Exchanges | Underlying Asset Value / Cash Flow |
| **Ownership** | Bearer Instrument (Private Keys) | Registered Ownership (KYC required) |
| **Reporting** | Tax (Capital Gains) | Tax + Regulatory Filings |


### Technical Data Model Extension

When modeling a "Security Token," your JSON needs to account for the Underlying Security it represents:

```json
{
  "instrument_id": "ST-772-APPLE-RE",
  "type": "CRYPTO_ASSET",
  "sub_type": "SECURITY_TOKEN",
  "isin": "US123456789",
  "underlying_asset_type": "REAL_ESTATE",
  "smart_contract": {
    "address": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    "network": "ETHEREUM",
    "standard": "ERC-1404" 
  },
  "compliance": {
    "kyc_required": true,
    "whitelist_id": "WL-9901",
    "transfer_restricted_until": "2027-01-01"
  }
}
```

## Crypto Asset as Security

When modeling a **Crypto Asset as a Security** (often called a Security Token), you are essentially merging the technical infrastructure of a blockchain with the regulatory requirements of traditional finance.

A complete model must handle the bearer nature of digital assets (private keys and addresses) alongside the registered nature of securities (KYC, ownership rights, and transfer restrictions).

### 1. The Core Data Pillars

A complete model is built on four distinct layers of data:

#### Layer 1: Technical (The On-Chain ID)

This identifies where the asset lives and how it is controlled.

- **Contract Address**: The specific hex address on the blockchain (e.g., 0x123...).
- **Network/Protocol**: The base layer (Ethereum, Polygon, Avalanche).
- **Token Standard**: The technical "rulebook" (e.g., ERC-1404 for restricted tokens or ERC-3643 for T-Rex compliance).
- **Wallet Address**: The specific address holding the position.

#### Layer 2: Regulatory (The Compliance ID)

This ensures the asset follows the laws of the jurisdiction it is issued in.

- **Standard Identifiers**: **ISIN** (International Securities Identification Number) or CUSIP.
- **Asset Classification**: (e.g., "Equity Token," "Debt Token," "Fractionalized Real Estate").
- **Whitelist/Registry ID**: A link to the database of verified identities (KYC/AML) allowed to hold the token.
- **Transfer Restrictions**: Rules such as "No transfers to US residents" or "Minimum 1-year hold period."

#### Layer 3: Economic (The Value)

- **Underlying Asset Link**: A reference to the physical or traditional asset it represents (e.g., a specific building or share of stock).
- **Total Supply / Cap Table**: How many tokens exist and who owns what.
- **Entitlements**: Rights to dividends, interest payments, or liquidation proceeds.

#### Layer 4: Governance (The Rights)

- **Voting Weight**: How many votes per token.
- **Proposal Rights**: Ability to initiate a corporate action on-chain.

### 2. Complete Technical Model (JSON)

In a professional wealth management system, the JSON object for a Security Token would look significantly more complex than a standard Bitcoin entry:

```json
{
  "instrument_id": "ST-7822-CH",
  "name": "Swiss Real Estate Token A",
  "isin": "CH1234567890",
  "type": "CRYPTO_ASSET",
  "sub_type": "SECURITY_TOKEN",
  "status": "ACTIVE",
  "currency": "CHF",
  "blockchain_details": {
    "network": "ETHEREUM_MAINNET",
    "contract_address": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
    "token_standard": "ERC-3643",
    "decimals": 18
  },
  "underlying_asset": {
    "category": "REAL_ESTATE",
    "property_ref": "PROP-ZURICH-01",
    "valuation_method": "ANNUAL_APPRAISAL"
  },
  "compliance_rules": {
    "kyc_required": true,
    "investor_type_allowed": ["ACCREDITED", "INSTITUTIONAL"],
    "prohibited_jurisdictions": ["US", "CN", "KP"],
    "transfer_lock_until": "2026-12-31"
  },
  "governance": {
    "has_voting_rights": true,
    "voting_ratio": 1.0,
    "dividend_policy": "QUARTERLY_CASH_DISTRIBUTION"
  }
}
```

### 3. The Lifecycle: From Issuance to Maturity

A complete model must also track the "state" of the crypto security:

### Token Lifecycle: Stages and Data Changes

| Stage | Data Change |
| :--- | :--- |
| **Issuance** | Total Supply is minted; ISIN is assigned. |
| **Primary Sale** | Tokens move to Whitelisted wallets. |
| **Secondary Trading** | Smart contract checks "Whitelist Status" before every transfer. |
| **Corporate Action** | Dividends are "Airdropped" (pushed) to token holders automatically. |
| **Redemption/Maturity** | Tokens are "Burned" (destroyed) in exchange for the final payout. |


### Summary: Key Differences in the Model

| Attribute | Standard Crypto (e.g., BTC) | Crypto as Security |
| :--- | :--- | :--- |
| **Identification** | Ticker / Address | **ISIN / Ticker / Address** |
| **Transferability** | Permissionless (anyone) | **Permissioned (only KYCed)** |
| **Value Source** | Supply & Demand | **Underlying Cash Flow / Assets** |
| **Legal Status** | Commodity / Currency | **Investment Contract** |

## How do crypto assets differ from traditional securities?

While native cryptocurrencies (like Bitcoin) often function as digital commodities, Security Tokens are explicitly categorized as financial instruments because they represent legal ownership or economic rights in an underlying asset.

Because they are regulated instruments, Security Tokens share many of the same core data attributes as Traditional Bonds, but they add technical layers like **Smart Contract Addresses** and **Permissioned Lists**.

### Data Attributes: Traditional Bond vs. Security Token

| Attribute | Traditional Bond | Security Token (on Blockchain) |
| :--- | :--- | :--- |
| **Primary ID** | **ISIN** or CUSIP | **ISIN + Smart Contract Address** |
| **Issuer** | Central Entity (Corp/Gov) | On-chain Issuer ID |
| **Principal** | Face / Par Value (e.g., $1,000) | Total Minted Supply |
| **Coupon** | Fixed/Floating Interest Rate | Automated Yield (via Smart Contract) |
| **Maturity** | Fixed Redemption Date | Automated "Burn" or Payout Logic |
| **Ownership** | Custodian Ledger entry | Wallet Address (on Distributed Ledger) |
| **Transfer** | T+2 Settlement via Broker/Bank | Near-Instant Settlement (T+Seconds) |
| **Compliance** | Manual/Regulatory checks | **Whitelisted Wallets** (Auto-KYC) |



