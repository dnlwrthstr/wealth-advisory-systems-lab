# Options in the Context of Derivatives

An **Option** is a financial derivative—a contract that derives its value from an "underlying" asset (like a stock, commodity, or index). Unlike a stock, where you own a piece of a company, an option represents the **right**, but not the obligation, to buy or sell that asset at a specific price within a set timeframe.

## The Two Faces of Options

| Type | Action | Market Outlook |
| :--- | :--- | :--- |
| **Call Option** | The right to **BUY** the asset. | **Bullish:** You expect the price to go up. |
| **Put Option** | The right to **SELL** the asset. | **Bearish:** You expect the price to go down. |

## Core Components of an Option

To define an option position in a portfolio, you must track these four variables:

- **Underlying Asset**: The security the option is "betting" on (e.g., Apple stock, Gold, or the S&P 500).

- **Strike Price**: The fixed price at which the option holder can buy or sell the underlying asset.

- **Expiration Date**: The "use-by" date. After this, the option becomes worthless.

- **Premium**: The price you pay (as a buyer) or receive (as a seller) for the contract.

## Why Use Options?

1. **Leverage**: You can control a large amount of stock with a relatively small amount of cash (the premium).
2. **Hedging (Insurance)**: Investors buy "Puts" to protect their portfolio against a market crash. It acts like an insurance policy that pays out if prices drop.
3. **Income Generation**: By "writing" (selling) options, investors can collect premiums, effectively getting paid to wait for a stock to reach a certain price.

## The Concept of "Moneyness"

This describes the relationship between the current market price of the underlying asset and the option's strike price.

- **In-the-Money (ITM)**: The option has intrinsic value. (e.g., A Call option with a \$100 strike when the stock is at \$110).

- **At-the-Money (ATM)**: The strike price is identical to the market price.
 
- **Out-of-the-Money (OTM)**: The option has no intrinsic value—only "hope" (time) value. (e.g., A Call option with a \$100 strike when the stock is only at \$90).**

## The "Greeks": Measuring Risk

In professional wealth management, options aren't just measured by price, but by their sensitivity to the market, known as "The Greeks."

| Greek | What it Measures |
| :--- | :--- |
| **Delta** | How much the option price moves for every &#36;1 move in the stock. |
| **Theta** | **Time Decay:** How much value the option loses every day as it gets closer to expiration. |
| **Vega** | Sensitivity to **Volatility**. If the market gets "nervous," Vega increases the option's price. |
| **Gamma** | The rate at which Delta changes. |

## Risks of Option Positions

Options are high-risk instruments and can lead to the total loss of the investment.

### 1. Time Decay (Theta Risk)

Options are high-risk instruments and can lead to the total loss of the investment.

### 2. Volatility Risk

You can be right about the direction of the stock but still lose money if the market's "expected volatility" drops, causing the premium to shrink.

### 3. Unlimited Risk (For Sellers)

If you sell (write) a "naked" call option, your potential loss is theoretically unlimited because there is no cap on how high a stock price can go.

## API & Data Implementation (OpenWealth)

When looking at options in a technical schema, two specific fields are critical:

### The Contract Multiplier

Most equity options represent 100 shares of the underlying stock.

- **Quantity**: 1 contract
- **Nultiplier**: 100
- **Exposure**: $\text{Quantity} \times \text{Multiplier} \times \text{Underlying Price}$

## Style: American vs. European

This defines when the option can be exercised:

- **American Style**: Can be exercised at any time before expiration (common for stocks).

- **European Style**: Can only be exercised on the expiration date (common for indices).

## Valuation Math

The value of an option position in a portfolio is::

$$\text{Position Value} = \text{Number of Contracts} \times \text{Multiplier} \times \text{Market Price of Option}$$

## Option as an Instrument

To model an option as an instrument in a financial system or database (like a JSON schema or SQL table), you need to capture both the **static identity** of the contract and its **dynamic risk profile**.

Here are the key values categorized by their functional role in a data model:

### 1. Core Identification (The Contract Terms)

These properties are "set in stone" when the contract is created. They define what the instrument is.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Option Type** | Enum | `CALL` or `PUT`. |
| **Underlying ID** | String/UUID | The ID of the asset (Stock, Index, Commodity) the option is tied to. |
| **Strike Price** | Decimal | The price at which the underlying can be bought/sold. |
| **Expiry Date** | Date/Timestamp | The date the contract ceases to exist. |
| **Exercise Style** | Enum | `AMERICAN` (anytime) or `EUROPEAN` (only at expiry). |
| **Contract Size** | Integer | The multiplier (usually `100` for equities). |

### 2. Valuation & Pricing Data

These values change constantly with the market. They are used to calculate the "Mark-to-Market" (MtM) value of a position.

- **Premium (Market Price)**: The current trading price of the option contract itself.

- **Intrinsic Value**: The "real" value if exercised today.
  - For a Call: $\max(0, \text{Underlying Price} - \text{Strike Price})$
  - For a Put: $\max(0, \text{Strike Price} - \text{Underlying Price})$
- **Extrinsic Value (Time Value)**: The portion of the premium not covered by intrinsic value (Premium - Intrinsic Value).

### 3. The "Greeks" (Risk & Sensitivity Model)

For a robust model, you must include the sensitivities. These tell your system how the option's value will react to external changes.

- **Delta ($\Delta$)**: Directional risk. How much the option price moves per $1 move in the underlying.
- **Gamma ($\Gamma$)**: The rate of change of Delta (acceleration).
- **Theta ($\Theta$)**: Time decay. The daily loss in value as expiry approaches.
- **Vega ($\nu$)**: Volatility risk. How much the price moves per 1% change in Implied Volatility.
- **Rho ($\rho$)**: Sensitivity to interest rate changes.

### 4. Settlement & Technical Metadata

Crucial for back-office systems and API integrations (like OpenWealth or FIX).

- **Settlement Method**: CASH (difference paid in money) or PHYSICAL (actual shares are moved).
- **Implied Volatility (IV)**: A percentage derived from the current market price that indicates how "volatile" the market expects the underlying to be.
- **Open Interest**: The total number of outstanding contracts that have not been settled.
- **In-the-Money Flag**: A boolean indicating if the option currently has intrinsic value.

#### Example Data Structure (JSON)

If you were to represent this in a digital instrument record, it might look like this:

````json
{
  "instrument_id": "OPT-AAPL-20260619-C-200",
  "type": "OPTION",
  "underlying_asset": "AAPL",
  "option_type": "CALL",
  "strike_price": 200.00,
  "expiry_date": "2026-06-19",
  "exercise_style": "AMERICAN",
  "contract_multiplier": 100,
  "settlement_type": "PHYSICAL",
  "market_data": {
    "last_price": 12.50,
    "implied_volatility": 0.24,
    "delta": 0.65,
    "theta": -0.04
  }
}
````
