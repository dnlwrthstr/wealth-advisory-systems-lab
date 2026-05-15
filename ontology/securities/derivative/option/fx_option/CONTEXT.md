# FX Options

## FX Options as a Financial Instrument

An **FX Option** is a derivative instrument that grants the holder the right, but not the obligation, to exchange one currency for another at a specific **Strike Price** on or before a pre-determined **Expiry Date**. Unlike FX Forwards, which are firm obligations, options provide flexibility for the buyer while placing a contractual requirement on the seller.

### Mandatory Technical Identifiers 

While many FX Options are traded Over-the-Counter (OTC), they require specific identifiers for risk management and regulatory reporting:

- **Option Type**: Defined as either a **Call** (right to buy the base currency) or a **Put** (right to sell the base currency).

-**Stxle**: Typically **European** (exercisable only at expiry) or **American** (exercisable at any time up to expiry).

- **Currency Pair**: The underlying currencies being exchanged (e.g., EUR/USD).

- **Counterparty ID**: The **Legal Entity Identifier (LEI)** of the option writer/seller.

### FX Option Data Attributes

In a financial data model, an FX Option requires the following technical fields to accurately calculate its Greeks and market value:

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Strike Price** | Decimal | The exchange rate at which the option can be exercised. |
| **Notional Amount** | Decimal | The face value of the currency protected by the option. |
| **Premium** | Decimal | The upfront, non-refundable cost paid by the buyer to the seller. |
| **Expiry Date** | Date | The final date and time the option remains valid. |
| **Settlement Date** | Date | The date the currency exchange actually occurs if exercised. |

- **Expiry vs. Settlement**: In the world of options, the **Expiry Date** is the "use it or lose it" deadline for the buyer. The **Settlement Date** is when the actual money or asset changes hands if that option was exercised.

- **Strike Price**: This is your "locked-in" price. If the market price is better than your strike price, the option is "In-the-Money" (ITM).