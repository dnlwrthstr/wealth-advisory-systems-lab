# Crypto Assets (Digital Assets) in a Portfolio Context

In the **CFI (ISO 10962:2021)** system, crypto assets are classified based on their "true nature" rather than just the fact that they are digital. There isn't one single "Crypto" category; instead, the system branches depending on whether the token is a security, a utility, or a reference instrument.

As of 2026, the classification typically falls into three main buckets:

## 1. Tokenized Traditional Assets (The "Financial" Route)

If a crypto asset represents a claim on a traditional financial instrument (like a tokenized bond or share of a company), it keeps the standard CFI category for that instrument (e.g., E for Equity or D for Debt).

-  **Code Example**: A tokenized fixed-rate bond might still be **D B F X F R**.
-  **Key Factor**: The token must confer the same legal rights as the paper version.

## 2. Referential Instruments (Category: T)

This is where "native" cryptocurrencies like **Bitcoin** or **Ethereum** usually live when they are treated as commodities or reference tools for pricing.

- **Category**: T (Referential Instruments)
- **Group**: M (Others/Miscellaneous)
- **Standard Code**: T M X X X X
- **Usage**: This code is frequently paired with a **DTI (Digital Token Identifier)** to provide the technical specifics of the blockchain it lives on.

## 3. Derivative Cryptos (Category: S or O)

If you are holding a "Crypto Future" or a "Total Return Swap" on a crypto index, it follows the **Derivatives** model we discussed earlier.

- **Category**: **S** (Swaps) or **O** (Options).
- **Attribute**: The 2nd character (Group) would likely be **T** (Commodities) or **M** (Others) depending on how the underlying crypto is viewed by the regulator.

### Comparison of Crypto Classifications

| Asset Type | CFI Category | Reasoning |
| :--- | :--- | :--- |
| **Stablecoins (Fiat-backed)** | **T** (Referential) or **L** (Loan) | Often viewed as a "claim" or a reference to a currency. |
| **Security Tokens (STOs)** | **E** (Equity) or **D** (Debt) | They represent ownership or debt in a legal entity. |
| **Native Coins (BTC/ETH)** | **T** (Referential) | Used as a benchmark or "digital commodity." |
| **NFTs** | **T** or **M** | Generally classified as miscellaneous "Referential" assets unless they grant financial rights. |

### Why the "T" Category is Important

The "T" category (Referential Instruments) was specifically expanded in the 2021 update to handle things that don't fit into traditional "Security" buckets. It allows the financial world to track Bitcoin or utility tokens without legally declaring them "Bonds" or "Equities," which would trigger massive regulatory hurdles.

> Pro-Tip for PMS: In a Portfolio Management System, you should link the CFI code to a DTI (ISO 24165). While the CFI tells the system what the asset is (e.g., a referential token), the DTI tells the system which technical ledger it exists on (e.g., Ethereum Mainnet vs. Polygon).
