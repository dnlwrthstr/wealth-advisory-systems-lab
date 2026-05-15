# Commodities

In the **CFI (ISO 10962)** standard, commodities are handled with a very specific logic: the system distinguishes between the physical commodity itself and the derivative contract used to trade it.

For a Portfolio Management System (PMS), you will almost never hold the physical "pile of gold" or "barrel of oil" as a security. Instead, you hold a derivative or a **referential instrument**.

## 1. Physical Commodities (Category: T)

Under the 2021 CFI update, physical commodities—when they need to be identified in a financial system—fall under **Category T (Referential Instruments)**.

- **Group C (Commodities)**: This is the specific group for raw materials.
- **Attributes**: The remaining characters define the sub-type (Energy, Agriculture, Metals).
- **CFI Example: T C E X X X** (Referential, Commodity, Energy).

## 2. Commodity Derivatives (The Most Common Type)

Most "commodity positions" in a portfolio are actually **Futures**, **Options**, or **Swaps**. These live in the derivative categories:

### A. Commodity Futures (Category: F)

- **Group T (Commodities)**: This is the primary group for futures.
- **CFI Example**: **F T S C S C**
  - **F** = Futures
  - **T** = Commodity
  - **S** = Standardized
  - **C** = Cash Settlement (or **P** for Physical)Commodity

### B. Commodity Swaps (Category: S)

Used by airlines to hedge fuel prices or miners to lock in gold prices.

- **Group T (Commodities)**: This is the primary group for swaps.
- **CFI Example: S T X T X C** (Swap, Commodity, Total Return).

## 3. The "Sub-Group" Breakdown (The 2nd/3rd Character)

When dealing with commodities, the CFI code gets very specific about what the "stuff" is. The system uses these identifiers:

| Character | Sub-Group | Examples |
| :--- | :--- | :--- |
| **E** | **Energy** | Crude Oil, Natural Gas, Electricity. |
| **A** | **Agricultural** | Corn, Wheat, Soybeans, Lean Hogs. |
| **M** | **Metals** | Gold, Silver, Copper, Lithium. |
| **I** | **Index** | Bloomberg Commodity Index (BCOM). |
| **P** | **Environmental** | Carbon Credits, Renewable Energy Certificates. |

## 4. Special Case: Carbon Credits (Environmental)

In modern ESG-focused portfolios, Carbon Credits are a massive new asset class.

- In CFI, these are classified under **Category T (Referential)** or **Category F (Futures)**.
- They use the sub-group **P** (Environmental).
- This allows a PMS to separate "Energy" (Oil) from "Environmental" (Carbon) even though both are technically commodities.

Summary of the PMS Model:

| Position Type | CFI Category | Why? |
| :--- | :--- | :--- |
| **Gold ETF** | **E** (Equity) | It’s a share in a trust, even if it tracks gold. |
| **Oil Future** | **F** (Future) | It's a contract to buy/sell at a later date. |
| **Physical Bullion** | **T** (Referential) | It’s the underlying "reference" asset. |
| **Commodity Swap** | **S** (Swap) | An exchange of cash flows based on a commodity price. |

> Pro-Tip: If your PMS tracks commodities, pay close attention to the 6th character (Settlement). A code ending in P (Physical) means you might literally have to take delivery of 1,000 barrels of oil if you don't sell the contract before it expires!