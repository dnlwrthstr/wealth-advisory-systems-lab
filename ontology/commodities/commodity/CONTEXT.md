# Commodity

A **Commodity** is a basic good used in commerce that is interchangeable with other goods of the same type. Unlike stocks (which represent company ownership) or bonds (which represent debt), commodities are physical "hard assets." They are the raw materials that fuel the global economy—from the gold in a watch to the oil in a car.

## Common Types of Commodities

| Category | Examples | Characteristics |
| :--- | :--- | :--- |
| **Precious Metals** | Gold, Silver, Platinum | Often used as a "store of value" or hedge against inflation. |
| **Energy** | Crude Oil, Natural Gas | Highly sensitive to geopolitical events and economic growth. |
| **Agriculture (Softs)** | Wheat, Coffee, Corn, Sugar | Driven by weather patterns and global consumption needs. |
| **Industrial Metals** | Copper, Aluminum, Nickel | "Doctor Copper": viewed as a pulse for global construction. |

## How Commodities Work

Commodities are unique because they are standardized. It doesn't matter where a bushel of wheat is grown; it is traded based on a set of quality specifications.

- **Spot Price**: The price for immediate delivery of the physical commodity.

- **Futures Price**: The price agreed upon today for delivery at a specific date in the future.

- **No Cash Flow**: Unlike stocks (dividends) or bonds (interest), commodities do not produce income. Your total return is based entirely on **price appreciation**.

## Why Invest in Commodities?

1. **Inflation Hedge**: When the cost of living rises, the price of raw materials usually rises with it. Gold, in particular, is a classic defense against a devaluing currency.
2. **Diversification**: Commodities often move differently than stocks and bonds. When the stock market crashes, commodities like gold may stay stable or rise.
3. **Supply & Demand Plays**: Investors bet on global trends—for example, buying Lithium or Copper to profit from the rise of electric vehicles.

## Key Components of a Commodity Position

### 1. The Method of Exposure

Most retail investors don't want 500 barrels of oil delivered to their front door. They use different "vehicles":

- **Physical**: Owning the actual asset (common for gold bars/coins held in a bank vault).

- **ETCs (Exchange Traded Commodities)**: Securities that track the price of a commodity.

- **Futures Contracts**: Legal agreements to buy or sell the asset at a future date.

### 2. The Quantity and Unit

Because commodities are physical, the measurement unit is vital for valuation.

- **Troy Ounces**: Precious metals.

- **Barrels**: Oil.

- **Metric Tons**: Industrial metals and grains.

### 3. Storage and Insurance (The "Carry")

If you own physical commodities, you have to pay to keep them safe.

- **Storage Costs**: Fees for warehouse or vault space.

- **Insurance**: Protecting the physical asset against theft or damage.

- **Cost of Carry**: The total cost of holding the physical asset (Storage + Insurance - any convenience yield).

## Technical Concepts: Contango vs. Backwardation

This is the "Price vs. Yield" equivalent for commodities. Since most investors use Futures Contracts, the relationship between the "Current" price and the "Future" price matters immensely.

- **Contango**: The future price is *higher* than the spot price. This usually happens when there are high storage costs. If you "roll" your position forward, you might lose money even if the price stays flat.

- **Backwardation**: The future price is lower than the spot price. This often happens during a supply shortage.

## Risks of Commodity Positions

### Volatility Risk

Commodities are notoriously "swingy." A sudden frost in Brazil can send coffee prices up 20% in a week; a geopolitical truce can tank oil prices overnight.

### Geopolitical Risk

Since many commodities come from specific regions (e.g., Oil from the Middle East, Palladium from Russia), political instability or trade sanctions can lead to massive price shocks.

### Liquidity Risk

While "Gold" is highly liquid, "Pink Pepper" or "Live Cattle" might be harder to sell quickly without moving the market price significantly.

## API & Data Implementation (OpenWealth / ISO 20022)

In financial data schemas, commodities are treated as a specialized instrument type.

### The Pricing Factor

As discussed in the Bond context, commodities often use a Price Factor of 1.0.

#### Example

f you own 10 Ounces of Gold and the price is 2,000.00, the math is a direct multiplication:

$$10 \times 2,000.00 = 20,000.00 \text{ USD}$$

#### Valuation Attributes

- **Instrument Currency**: The currency the commodity is quoted in (usually USD for global markets).

- **Safe Custody**: A flag indicating if the bank is physically holding the asset (allocated) or if the investor just has a claim on a pool of the asset (unallocated).


## Commodity as a security

To treat a Commodity as a security within a digital portfolio, a financial system must translate a physical pile of raw material into a standardized "financial instrument." This allows a bank to calculate its value, risk, and weight alongside stocks and bonds.

### 1. The Unit of Measure (UOM)

Unlike stocks (Units/Shares) or Cash (Currency), a commodity instrument is defined by its physical measurement. This is the most critical metadata point for accurate valuation.

- **Standard Units**: OZT (Troy Ounces for Gold/Silver), BBL (Barrels for Oil), MT (Metric Tons for Copper).
- **Contract Size**: For derivatives, the "Multiplier." One Gold future contract usually represents 100 Troy Ounces.

### 2. Quotation Type

Commodities are almost always quoted in Unit Pricing, but the currency is nearly universal.

- **Quote Currency**: Usually **USD**. Even if a European investor buys Gold, the global "Instrument Price" is typically in USD, requiring an FX conversion for the portfolio's base currency.
- **Price Factor**: Usually 1.0, meaning the Market Value = $Quantity \times Price$.

### 3. Custody & Ownership Model

Because commodities are physical, the "Where" and "How" of ownership changes the instrument's risk profile:

- **Allocated**: The investor owns specific, numbered bars (e.g., Gold Bar #1234). This is a "Physical" instrument type.
- **Unallocated**: The investor has a general claim against the bank's total stock of the metal. This is treated more like a "Credit" or "Liability" of the bank.
- **Paper/Synthetic**: The instrument is an ETC (Exchange Traded Commodity) or a Future. Here, the "Underlying" is the commodity, but the instrument itself is a transferable security with an **ISIN**.

### 4. Storage and Carry Metadata

A commodity instrument often has "negative yield" attributes known as **Holding Costs**:

- **Storage Rate**: A basis point or flat fee deducted for vaulting (common in physical precious metals). 
- **Insurance Fee**: The cost to protect the physical asset.
- **Last Physical Inspection Date**: For high-value physical holdings, the date the auditor verified the existence of the asset.

### 5. Product Lifecycle (Futures/Forwards)

If the commodity is held via a contract rather than physical bars, it has a "Pulse":

- **Expiry Date**: When the contract ends.
- **Roll Schedule**: The logic for selling the "Front Month" contract and buying the "Next Month" contract to avoid physical delivery.

### JSON Schema: Commodity Instrument

```json
{
  "instrumentId": "PHYS-GOLD-OZT",
  "instrumentType": "COMMODITY_PHYSICAL",
  "identifiers": {
    "ticker": "XAU",
    "commonName": "Gold Spot / Troy Oz"
  },
  "attributes": {
    "unitOfMeasure": "OZT",
    "purity": "0.9999",
    "isAllocated": true,
    "storageLocation": "ZURICH-VAULT-04"
  },
  "valuation": {
    "quantity": 50.00,
    "unitPrice": 2045.50,
    "priceCurrency": "USD",
    "marketValueBase": 102275.00
  },
  "costs": {
    "annualStorageFeePct": 0.0025,
    "accruedStorageFees": 42.10
  }
}
```

### Comparison: Physical Instrument vs. Commodity ETF/ETC

| Feature | Physical Instrument (Gold Bar) | Commodity ETF/ETC |
| :--- | :--- | :--- |
| **Identifier** | Internal Ref / Serial # | ISIN (e.g., `IEOOB579F325`) |
| **Liquidity** | T+2 or slower (requires transport) | T+2 (Exchange Traded) |
| **Storage** | Paid by investor | Built into the Fund's Expense Ratio |
| **Counterparty** | The Vault/Custodian | The Fund Issuer |

