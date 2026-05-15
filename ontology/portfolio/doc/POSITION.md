# Position in a PMS

Modeling positions for a Portfolio Management System (PMS) aligned with the **Open Wealth Standard** requires a shift from traditional, siloed accounting toward a highly granular, API-first architecture.

In Open Wealth, "Positions" aren't just snapshots; they are data-rich nodes that link holdings to market data, valuations, and specific tax/legal constraints.

## 1. Core Position Entity Structure

To meet the standard, your position model should differentiate between the **Security** (what it is) and the **Holding** (how much you have and its cost).

| Field Category | Key Attributes | Purpose |
| :--- | :--- | :--- |
| **Identifiers** | `positionID`, `accountID`, `instrumentID` | Unique mapping across systems. |
| **Quantity** | `totalQuantity`, `blockedQuantity`, `settledQuantity` | Handling "pending" trades and collateral. |
| **Valuation** | `marketPrice`, `priceCurrency`, `marketValue` | Real-time or EOD valuation. |
| **Cost Basis** | `costPrice`, `acquisitionCost`, `bookValue` | For P&L and tax reporting. |
| **Performance** | `unrealizedPL`, `accruedInterest` | Key metrics for the end client. |

### Understanding Position Management

This data structure is fundamental for any Portfolio Management System (PMS) to ensure accurate reporting and trading operations:

- **Settlement Tracking**: By separating totalQuantity from settledQuantity, the system can prevent "short selling" by mistake or identifies assets that are currently tied up as collateral (blockedQuantity).
- **P&L Calculations**: The Cost Basis fields are used to calculate the unrealizedPL (Profit and Loss). This is essential for both client performance reporting and determining potential tax liabilities.
- **Valuation**: Real-time systems typically update marketPrice via a data feed API, while back-office systems may rely on End-of-Day (EOD) pricing.

## 2. The Relationship Model

In an Open Wealth context, positions exist within a hierarchy. You should model them as part of a **Holding Container**.

### Key Relationships:

- **Portfolio (Container)**: The highest level (e.g., "The Smith Family Trust").
- **Account/Sub-Account**: Positions should be tagged to specific accounts (e.g., Cash, Custody, or Lombard).
- **Instrument Metadata**: Instead of bloating the position table, link to a Central Security Master (ISIN, FIGI, Asset Class, ESG Rating).

## 3. Handling Asset Specifics

Open Wealth emphasizes consistency across different asset types. Your model needs to handle "Polymorphic" attributes:

- **Fixed Income**: Must include accruedInterest and daysToMaturity.
- **Derivatives/Options**: Must include underlyingInstrumentID, strikePrice, and expiryDate.
- **Cash**: Often modeled as a position where the instrumentID is a currency (e.g., USD) and the price is always 1.

## 4. Open Wealth API Alignment

When designing the API endpoints for these positions, follow the RESTful patterns suggested by the standard:

- **GET /positions**: Return a list of all holdings for a specific accountId.
- **Granularity**: Ensure you can filter by assetClass or custodian.
- **Time-Series**: The standard often requires "As-Of" reporting. Your database should support temporal queries so you can pull positions for any historical date.

## 5. Implementation Tip: The "Calculated" vs "Stored" Debate

For a modern PMS, avoid storing volatile data like marketValue directly in your primary Positions table. Instead:

1. Store **Quantity** and **Cost Basis**.
2. Fetch **Market Price** from a Pricing Service.
3. Calculate **Market Value** on the fly or in a caching layer ($Quantity \times Price$). This ensures that a price update automatically refreshes the entire portfolio without bulk-updating position rows.

## Open Wealth Position Schema (Draft)

Following the **Open Wealth API** specifications (specifically the Positions and Instruments endpoints), here is a structured JSON schema.

This model separates the **Position** (the holding) from the **Instrument** (the security) and includes the necessary metadata for valuation and reconciliation.

```json
{
  "positionId": "pos-987654321",
  "accountId": "acc-df82-4110",
  "status": "ACTIVE",
  "tradeDate": "2026-02-18T14:30:00Z",
  "settlementDate": "2026-02-20T14:30:00Z",
  
  "instrument": {
    "instrumentId": "inst-apple-123",
    "identifiers": {
      "isin": "US0378331002",
      "ticker": "AAPL",
      "figi": "BBG000B9XRY4"
    },
    "type": "EQUITY",
    "currency": "USD"
  },

  "quantity": {
    "amount": 150.00,
    "unit": "SHARES",
    "blocked": 0.00,
    "settled": 150.00
  },

  "valuation": {
    "marketPrice": 192.50,
    "priceDate": "2026-02-19T09:00:00Z",
    "marketValue": 28875.00,
    "valuationCurrency": "USD",
    "fxRateToPortfolio": 1.0
  },

  "costBasis": {
    "averagePrice": 155.20,
    "totalCost": 23280.00,
    "unrealizedPL": 5595.00,
    "unrealizedPLPercentage": 24.03
  },

  "accruals": {
    "accruedInterest": 0.00,
    "pendingDividends": 36.00
  },

  "metadata": {
    "custodianId": "cust-global-bank-01",
    "lastUpdated": "2026-02-19T09:34:00Z"
  }
}
```
#### Key Architectural Decisions

- **The Identifier Trio**: Open Wealth thrives on interoperability. By including isin, ticker, and figi within the instrument object, you ensure your PMS can talk to external custodians and market data providers (like Bloomberg or Refinitiv) without translation errors.
- **Quantity Segmentation**: Notice the distinction between amount and settled. In a live PMS, trades that haven't reached $T+2$ or $T+3$ settlement should not be treated as fully "owned" for certain regulatory or tax reports.
- **The Valuation Snapshot**: While I mentioned earlier that calculation is often best done on-the-fly, the Open Wealth Standard usually expects a "snapshot" via API. This schema provides the result of the calculation ($Quantity \times Price$).
- **FX Normalization**: If the client's portfolio is in EUR but the stock is in USD, your model must store the fxRateToPortfolio used at the time of the snapshot to avoid "ghost" P&L fluctuations.

##  Transaction (Journal)

To build a PMS that truly mirrors the Open Wealth Standard, your "Positions" (the state) must be perfectly reconciled with your "Transactions" (the change). In Open Wealth, transactions are typically modeled as Journals.

A transaction doesn't just change a quantity; it captures the movement of value between cash and securities, including fees, taxes, and FX impacts.

### 1. Transaction (Journal) Schema

This model follows the "Double-Entry" logic preferred by modern wealth platforms to ensure the portfolio always balances.

```json
{
  "transactionId": "txn-550e8400-e29b",
  "externalReference": "CUST-TRADE-12345",
  "accountId": "acc-df82-4110",
  "type": "BUY", 
  "subType": "MARKET_ORDER",
  "bookingDate": "2026-02-18T14:30:00Z",
  "valueDate": "2026-02-20T00:00:00Z",

  "instrument": {
    "isin": "US0378331002",
    "currency": "USD"
  },

  "quantity": 10.0,
  "unitPrice": 190.50,
  
  "amounts": {
    "grossAmount": 1905.00,
    "netAmount": 1912.50,
    "currency": "USD",
    "fees": [
      {"type": "BROKERAGE", "amount": 5.00, "currency": "USD"},
      {"type": "STAMP_DUTY", "amount": 2.50, "currency": "USD"}
    ]
  },

  "fx": {
    "pair": "USD/EUR",
    "rate": 0.92,
    "localNetAmount": 1759.50
  }
}
```

## 2. The Interaction: How Transactions Update Positions

In a robust PMS, you don't just "overwrite" a position. You trigger a **Position Engine** that processes the journal entry.

- **Cost Basis Adjustment**: When a *BUY* occurs, the engine recalculates the *averagePrice* using the $Net Amount / Quantity$.
- **Corporate Actions**: If you receive a *DIVIDEND* transaction, the *Position* entity doesn't change in quantity, but its *totalReturns* or accruedDividends field is updated.
- **Reconciliation**: Open Wealth recommends a daily "Position-to-Transaction" check. If $Starting Position + Transactions \neq Ending Position$, an alert is triggered.


## 3. Handling Complex "Open Wealth" Events

The standard requires specific handling for events that traditional systems often overlook:

| Event Type | Modeling Requirement |
| :--- | :--- |
| **Transfer In/Out** | Must include "Acquisition Date" and "Original Cost" to maintain tax lots. |
| **Stock Split** | A non-cash transaction that multiplies `Quantity` and divides `Average Price`. |
| **Tax Reclaim** | A transaction linked to a specific dividend event, often settled months later. |

### Understanding Lifecycle Events

The attributes in this table ensure that the historical integrity of a position is maintained when its structure changes:

- **Tax Lot Management**: For **Transfers**, capturing the original cost and date is vital for accurate capital gains tax calculations later. Without this "back-dated" info, the system might default to a $0 cost basis, leading to over-taxation.
- **Adjusted Cost Basis**: During a **Stock Split**, the total value of the position remains the same, but the internal math must update to prevent artificial P&L spikes.
  - Example: A 2-for-1 split doubles your shares but halves the price per share. 
- **Accrual Matching: Tax Reclaims** often create a "reconciling item" in portfolios. Because they settle much later than the dividend itself, the system must link them back to the original event to ensure the total net yield of the asset is reported correctly.

## 4. Implementation Logic: "The Ledger"

To remain close to the Open Wealth standard, treat your Positions table as a **Read Model** (optimized for fast UI/API display) and your Transactions table as the **Source of Truth**. If you ever lose your position data, you should be able to replay all transactions from "Day Zero" to reconstruct the exact portfolio state.

To implement this in a relational database while maintaining Open Wealth compliance, you need a schema that supports Temporal Data (tracking changes over time) and Double-Entry integrity.

In this model, the positions table acts as your "Live Snapshot," while the transactions and ledger_entries tables provide the immutable audit trail.

### PostgreSQL Schema for Open Wealth Positions

```sql
-- 1. Instrument Master: The "What"
CREATE TABLE instruments (
    instrument_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isin VARCHAR(12) UNIQUE,
    ticker VARCHAR(20),
    name VARCHAR(255) NOT NULL,
    asset_class VARCHAR(50), -- e.g., 'EQUITY', 'FIXED_INC', 'CASH'
    currency_code CHAR(3) NOT NULL, -- ISO 4217
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Transaction Header: The "Event"
CREATE TABLE transactions (
    tx_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    instrument_id UUID REFERENCES instruments(instrument_id),
    tx_type VARCHAR(20) NOT NULL, -- 'BUY', 'SELL', 'DIVIDEND', 'TRANSFER'
    booking_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    value_date DATE NOT NULL,
    quantity DECIMAL(24, 10),
    unit_price DECIMAL(24, 10),
    net_amount DECIMAL(24, 10) NOT NULL, -- Total cash impact
    currency_code CHAR(3) NOT NULL,
    status VARCHAR(20) DEFAULT 'SETTLED'
);

-- 3. The Position Snapshot: The "State"
CREATE TABLE positions (
    account_id UUID NOT NULL,
    instrument_id UUID REFERENCES instruments(instrument_id),
    total_quantity DECIMAL(24, 10) DEFAULT 0,
    locked_quantity DECIMAL(24, 10) DEFAULT 0,
    avg_cost_price DECIMAL(24, 10) DEFAULT 0,
    total_acquisition_cost DECIMAL(24, 10) DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, instrument_id)
);

-- 4. Ledger Entries: The "Double Entry" (Audit Trail)
-- Every transaction creates at least two rows here: one for the Asset and one for Cash.
CREATE TABLE ledger_entries (
    ledger_id SERIAL PRIMARY KEY,
    tx_id UUID REFERENCES transactions(tx_id),
    account_id UUID NOT NULL,
    entry_type VARCHAR(20), -- 'ASSET_INCREASE', 'CASH_DECREASE', etc.
    amount DECIMAL(24, 10) NOT NULL,
    currency_code CHAR(3) NOT NULL
);
```

### Key Implementation Considerations

#### 1. The "Average Cost" Calculation

To stay close to standard accounting (WACO - Weighted Average Cost), your application logic or a database trigger should update positions every time a BUY or SELL transaction is finalized.

$$
AvgCost = \frac{TotalAcquisitionCost_{old} + NetAmount_{new}}{TotalQuantity_{old} + Quantity_{new}}
$$

#### 2. Position Reconciliation

Open Wealth requires high transparency. You should implement a "Daily Position Log" (or use a TimescaleDB hypertable) to store the EOD (End of Day) state of the positions table. This allows you to answer the API request: "What was the position on Jan 1st, 2026?"

#### 3. Handling "Cash as a Position"

In many PMS designs, Cash is simply another instrument where instrument_id points to a currency object (like USD) with a constant price of 1.00. This simplifies your UI logic because everything—from Apple stock to Euro cash—is just a row in the positions table.

> Logic Tip: The "Shadow" Position
> 
> When a trade is executed but not yet settled, you update locked_quantity or create a "Pending" position record. This prevents the user from selling the same shares twice while the first trade is still in the clearing house.

### Position Engine -Psedocode

To implement the logic of an Open Wealth-compliant PMS, you need a robust **Position Engine**. This script demonstrates how to process a transaction (a "Journal Entry") to update a position, specifically handling the **Weighted Average Cost (WAC)** and currency normalization.

This script assumes a "Position-as-a-Service" model where the transaction is the trigger and the position is the resulting state.

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

@dataclass
class Transaction:
    tx_id: str
    account_id: str
    instrument_id: str
    tx_type: str  # 'BUY', 'SELL', 'DIVIDEND'
    quantity: Decimal
    price: Decimal
    fees: Decimal
    currency: str
    settlement_date: datetime

@dataclass
class Position:
    instrument_id: str
    total_quantity: Decimal = Decimal('0')
    avg_cost: Decimal = Decimal('0')
    total_cost_basis: Decimal = Decimal('0')
    currency: str = "USD"

    def process_transaction(self, tx: Transaction):
        """
        Updates the raw_data state based on Open Wealth transaction logic.
        """
        if tx.tx_type == "BUY":
            # Net Amount includes fees for cost basis
            net_amount = (tx.quantity * tx.price) + tx.fees
            
            # Update Total Cost and Quantity
            self.total_cost_basis += net_amount
            self.total_quantity += tx.quantity
            
            # Recalculate Weighted Average Cost
            if self.total_quantity > 0:
                self.avg_cost = self.total_cost_basis / self.total_quantity

        elif tx.tx_type == "SELL":
            if tx.quantity > self.total_quantity:
                raise ValueError("Inadequate quantity for sell order (Short selling not allowed in this model)")
            
            # When selling, we reduce cost basis proportionally to the quantity sold
            # (Maintains the same Average Cost)
            reduction_ratio = tx.quantity / self.total_quantity
            self.total_cost_basis -= (self.total_cost_basis * reduction_ratio)
            self.total_quantity -= tx.quantity
            
            # If raw_data is closed, reset avg_cost
            if self.total_quantity == 0:
                self.avg_cost = Decimal('0')

    def __repr__(self):
        return (f"Position({self.instrument_id}): Qty={self.total_quantity}, "
                f"AvgCost={self.avg_cost:.2f}, TotalBasis={self.total_cost_basis:.2f}")

# --- Example Usage ---

# 1. Initialize an empty raw_data for Apple (AAPL)
aapl_pos = Position(instrument_id="US0378331002", currency="USD")

# 2. First Buy: 10 shares @ $150 + $5 fee
tx1 = Transaction("tx-001", "acc-1", "US0378331002", "BUY", Decimal('10'), Decimal('150'), Decimal('5'), "USD", datetime.now())
aapl_pos.process_transaction(tx1)
print(f"After Buy 1: {aapl_pos}")

# 3. Second Buy: 5 shares @ $160 + $5 fee
tx2 = Transaction("tx-002", "acc-1", "US0378331002", "BUY", Decimal('5'), Decimal('160'), Decimal('5'), "USD", datetime.now())
aapl_pos.process_transaction(tx2)
print(f"After Buy 2: {aapl_pos}")

# 4. Partial Sell: 7 shares @ $180 (Price doesn't affect cost basis, only the quantity does)
tx3 = Transaction("tx-003", "acc-1", "US0378331002", "SELL", Decimal('7'), Decimal('180'), Decimal('10'), "USD", datetime.now())
aapl_pos.process_transaction(tx3)
print(f"After Sell:   {aapl_pos}")
```

#### Why this approach fits the Standard

1. **Immutable Cost Basis**: Notice that during a SELL, the avg_cost remains unchanged. This is a core requirement for calculating **Unrealized P&L** correctly later ($MarketValue - CostBasis$).
2. **Fee Capitalization**: In wealth management, buying fees are typically added to the cost basis (making the "break-even" price higher), while selling fees are treated as an expense.
3. **Decimal Precision**: The use of Decimal instead of float is non-negotiable for financial systems to avoid rounding errors in sub-cent increments.

### Multi Currency Support

To handle a multi-currency environment (common in Swiss and European wealth management), your Position Engine must track the **Local Currency** (the asset's denomination) and the **Base Currency** (the portfolio's reporting currency).

In Open Wealth, this is critical because P&L is often split into **Market P&L** (price change) and **FX P&L** (currency fluctuation).

#### Multi-Currency Position Engine

This extended script introduces a base_currency and handles the FX conversion logic during the transaction.

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Transaction:
    tx_id: str
    instrument_id: str
    tx_type: str  # 'BUY', 'SELL'
    quantity: Decimal
    price: Decimal  # In Local Currency
    fees: Decimal   # In Local Currency
    local_currency: str
    fx_rate: Decimal  # Rate to convert Local -> Base (e.g., USD/CHF)
    settlement_date: datetime

@dataclass
class MultiCurrencyPosition:
    instrument_id: str
    local_currency: str
    base_currency: str
    
    # State in Local Currency
    total_quantity: Decimal = Decimal('0')
    
    # State in Base Currency (Reporting)
    total_cost_base: Decimal = Decimal('0') 
    avg_cost_base: Decimal = Decimal('0')

    def process_transaction(self, tx: Transaction):
        # 1. Calculate Local Net Amount
        local_net = (tx.quantity * tx.price) + (tx.fees if tx.tx_type == "BUY" else -tx.fees)
        
        # 2. Convert to Base Currency using the transaction's spot rate
        base_net = local_net * tx.fx_rate

        if tx.tx_type == "BUY":
            self.total_quantity += tx.quantity
            self.total_cost_base += base_net
            self.avg_cost_base = self.total_cost_base / self.total_quantity
            
        elif tx.tx_type == "SELL":
            if tx.quantity > self.total_quantity:
                raise ValueError("Short selling not permitted.")
            
            # Reduce cost basis proportionally in Base Currency
            reduction_ratio = tx.quantity / self.total_quantity
            self.total_cost_base -= (self.total_cost_base * reduction_ratio)
            self.total_quantity -= tx.quantity
            
            if self.total_quantity == 0:
                self.avg_cost_base = Decimal('0')

    def get_valuation(self, current_price: Decimal, current_fx_rate: Decimal):
        """
        Calculates Unrealized P&L split by Market and FX.
        """
        market_value_base = self.total_quantity * current_price * current_fx_rate
        total_pnl_base = market_value_base - self.total_cost_base
        return {
            "market_value_base": market_value_base,
            "total_pnl_base": total_pnl_base,
            "cost_basis_base": self.total_cost_base
        }

# --- Example: Buying AAPL (USD) in a CHF Portfolio ---
pos = MultiCurrencyPosition("AAPL", "USD", "CHF")

# Buy 10 shares @ $150. FX Rate USD/CHF = 0.88
tx = Transaction("tx-1", "AAPL", "BUY", Decimal('10'), Decimal('150'), Decimal('5'), "USD", Decimal('0.88'), datetime.now())
pos.process_transaction(tx)

print(f"Qty: {pos.total_quantity}")
print(f"Total Cost (CHF): {pos.total_cost_base}") # (1500 + 5) * 0.88 = 1324.40
```
#### Key Open Wealth Concepts Implemented

1. **The "Cost Filter"**: By storing the total_cost_base at the time of trade, you "lock in" the historical FX rate for the cost basis.
2. **Unrealized P&L Calculation**: To show the user their performance, you compare the **Current Market Value** (Current Price $\times$ Current FX) against the **Historical Cost Basis** (The amount actually spent in Base Currency).
3. **Accuracy**: $24.10$ decimal precision is the standard for Open Wealth to ensure that even small fractional share movements or crypto-assets don't suffer from floating-point drift.

#### Integration Hint

In a full PMS, you wouldn't manually pass fx_rate to the transaction. Your system would have an **FX Service** that provides the mid-market rate for the value_date of the transaction automatically.

### Valuation and P&L

To calculate the valuation and P&L for these positions according to the Open Wealth Standard, you must distinguish between performance driven by the **asset price** and performance driven by **currency fluctuations**.

This is achieved by comparing the "Cost Basis" (locked at the historical FX rate) against the "Current Market Value" (calculated at the current FX rate).

#### 1. Valuation Logic Schema

In a production PMS, the valuation is often a "View" or a calculated object rather than a static table.

| Metric | Calculation Formula | Purpose |
| :--- | :--- | :--- |
| **Market Value (Local)** | $Quantity \times CurrentPrice_{Local}$ | Value in the asset's currency. |
| **Market Value (Base)** | $MarketValue_{Local} \times CurrentFX$ | Value in the portfolio's reporting currency. |
| **Total P&L (Base)** | $MarketValue_{Base} - TotalCost_{Base}$ | The absolute gain/loss. |
| **FX P&L (Base)** | $(MarketValue_{Local} \times CurrentFX) - (MarketValue_{Local} \times CostFX)$ | Gain/loss due solely to currency moves. |

#### Understanding FX Impact on P&L

The formula for **FX P&L (Base)** is particularly important for international portfolios. It isolates the impact of currency fluctuations from the actual performance of the underlying asset:

- **Asset Performance**: If the local price of a stock goes up, your **Total P&L** increases.
- **Currency Performance**: If the local currency weakens against your base currency, your **FX P&L** will decrease, even if the stock price remains unchanged.By subtracting the value at the original exchange rate ($CostFX$) from the value at the current rate ($CurrentFX$), managers can see if their international gains are being "eaten" by unfavorable exchange rates.

### 2. Python Valuation Method

Expanding on our previous MultiCurrencyPosition class, we add a method to calculate these granular P&L metrics.

```python
def calculate_pnl(self, current_price: Decimal, current_fx: Decimal):
    # 1. Current Market Values
    market_value_local = self.total_quantity * current_price
    market_value_base = market_value_local * current_fx
    
    # 2. Total P&L in Base Currency
    total_pnl_base = market_value_base - self.total_cost_base
    
    # 3. FX P&L Component 
    # (How much of the P&L came from the change in FX rate since purchase?)
    # We use the 'Average Cost FX' which is implied by: TotalCostBase / (TotalQuantity * AvgPriceLocal)
    # For simplicity, we can isolate FX impact by comparing current value at current FX vs original FX.
    historical_fx_impact = market_value_local * (self.total_cost_base / (self.total_quantity * (self.total_cost_base / (self.total_quantity * self.avg_cost_base)) if self.total_quantity > 0 else 1))
    
    # Simplified FX P&L: (Current Local Value * Current FX) - (Current Local Value * Historical FX)
    avg_historical_fx = self.total_cost_base / (self.total_quantity * (self.avg_cost_base / (self.total_cost_base/self.total_quantity)) if self.total_quantity > 0 else 1) # conceptual
    
    return {
        "instrument_id": self.instrument_id,
        "market_value_base": round(market_value_base, 2),
        "total_pnl_base": round(total_pnl_base, 2),
        "pnl_percentage": round((total_pnl_base / self.total_cost_base) * 100, 2) if self.total_cost_base != 0 else 0
    }
```

### 3. Open Wealth Performance Attribution

When reporting to clients under Open Wealth, the system should be able to break down the **Total Return** into three buckets. This ensures transparency, especially in volatile markets.

- **Price Return**: Change in the instrument price ($P_1 - P_0$).
- **FX Return**: Change in the currency value ($FX_1 - FX_0$).
- **Income Return**: Dividends or interest received during the holding period.

### 4. Implementation Strategy: The "As-Of" Valuation

To satisfy audit requirements, your system should store these valuations in a Position History table at the end of every business day (EOD).

```sql
CREATE TABLE position_valuations (
    valuation_date DATE NOT NULL,
    account_id UUID NOT NULL,
    instrument_id UUID NOT NULL,
    market_value_base DECIMAL(24, 10),
    unrealized_pnl_base DECIMAL(24, 10),
    fx_rate_used DECIMAL(24, 10),
    PRIMARY KEY (valuation_date, account_id, instrument_id)
);
```

## Portfolio Aggregator

To complete the model, you need a Portfolio Aggregator. This layer rolls up individual positions into a single "Golden Record" of the portfolio’s health.

In the Open Wealth Standard, a portfolio isn't just the sum of its stocks; it includes **Cash Balances, Accrued Interest, and Total Exposure**.

### 1. The Portfolio Summary Schema

The aggregator should produce a summary object that answers the question: **"What is the client's total wealth right now?"**

| Component | Logic |
| :--- | :--- |
| **Assets Value** | $\sum \text{Market Value of all non-cash positions}$ |
| **Cash Value** | $\sum \text{Balance of all currency sub-accounts}$ |
| **Gross Value** | $Assets + Cash$ |
| **Liabilities** | Borrowing (Lombard loans) or short positions |
| **Net Wealth** | $GrossValue - Liabilities$ |

### 2. Python Portfolio Aggregator

This script aggregates the MultiCurrencyPosition objects we created earlier and calculates the portfolio-level P&L.

```python
class Portfolio:
    def __init__(self, portfolio_id: str, base_currency: str):
        self.portfolio_id = portfolio_id
        self.base_currency = base_currency
        self.positions = {} # instrument_id -> MultiCurrencyPosition

    def add_position(self, pos: MultiCurrencyPosition):
        self.positions[pos.instrument_id] = pos

    def get_summary(self, market_data: dict):
        """
        market_data format: { 'ISIN': {'price': Decimal, 'fx': Decimal} }
        """
        summary = {
            "total_market_value": Decimal('0'),
            "total_cost_basis": Decimal('0'),
            "unrealized_pnl": Decimal('0'),
            "allocations": {} # Asset Class Breakdown
        }

        for isin, pos in self.positions.items():
            data = market_data.get(isin)
            if not data: continue

            val = pos.calculate_pnl(data['price'], data['fx'])
            
            summary["total_market_value"] += val["market_value_base"]
            summary["total_cost_basis"] += val["cost_basis_base"]
            summary["unrealized_pnl"] += val["total_pnl_base"]

        # Calculate Total Performance %
        if summary["total_cost_basis"] > 0:
            summary["total_return_pct"] = (summary["unrealized_pnl"] / summary["total_cost_basis"]) * 100
        
        return summary
```

### 3. Data Visualization: Asset Allocation

Open Wealth consumers (like mobile banking apps or reporting engines) expect data to be "sliceable." Your aggregator should group positions by:

- **Asset Class** (Equity, Fixed Income, Cash, Alternatives)
- **Currency Exposure** (How much of my wealth is in USD vs. CHF?)
- **Sector/Region** (Tech vs. Energy, North America vs. Emerging Markets)

### 4. Handling "Cash as a Position"

A common mistake is treating Cash as a separate table. To be "standard-ready," **treat Cash as a Position** where:

- **Instrument**: The Currency Code (e.g., "USD").
- **Price**: Always 1.00.
- **FX Rate**: The spot rate for that currency to the Portfolio Base Currency.

This allows your aggregator to run the exact same logic for a bank account as it does for Apple stock.

### 5. Final Implementation Checklist

1. **Temporal Consistency**: Does your aggregator use market prices from the same timestamp for all positions?
2. **Dirty Flags**: Does your system mark a portfolio as "Dirty" (needing recalculation) whenever a new transaction is injected?
3. **Audit Trail**: Can you reproduce the 2025-12-31 valuation today?

