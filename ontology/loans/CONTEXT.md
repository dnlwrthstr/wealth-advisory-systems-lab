# Loans

This ontology defines concepts related to loans, including loan types, loan statuses, and loan terms.

Under the CFI (ISO 10962:2021) standard, loans are categorized under the letter "L". This category is distinct because, unlike bonds (Category D), these are typically private contracts that are not intended for public trading on an exchange.

The CFI model for a loan consists of six characters, where each position represents a specific attribute of the debt.

## The 6-Character CFI Structure for Loans (L)

### 1st Character: Category

- L – This always stands for Loan.

### 2nd Character: Group (The "Type" of Loan)

This identifies what kind of loan it is or what it is secured by.

- M – Mortgages (Secured by real estate)
- C – Commercial Loans (Business loans)
- P – Consumer Loans (Personal loans, auto loans)
- G – Government/Municipal Loans
- I – Institutional Loans (Interbank lending)

### 3rd Character: Type of Interest

- F – Fixed Rate (The interest rate never changes)
- V – Variable/Floating (The rate moves with an index like LIBOR/SOFR)
- Z – Zero Interest

### 4th Character: Amortization Type

- P – Planned/Scheduled (Regular payments of principal and interest)
- B – Balloon (Small payments with one giant payment at the end)
- I – Interest Only (No principal paid until the very end)

### 5th Character: Guarantee/Security

- S – Secured (Backed by collateral like a house or car)
- U – Unsecured (Based only on the borrower's credit)
- G – Guaranteed (A third party promises to pay if the borrower fails)

### 6th Character: Form of Settlement

- C – Cash (The most common; payments are made in currency)
- P – Physical (Rare for loans, but involves the transfer of an actual asset)

## Real-World Examples

To see how this "model" works in practice, let's build two common loan types:

### Example 1: A Standard 30-Year Fixed Home Mortgage

The code would be: **L M F P S C**

- L: Loan
- M: Mortgage
- F: Fixed Rate
- P: Planned Amortization
- S: Secured (by the house)
- C: Cash Settlement

### Example 2: An Unsecured Variable-Rate Credit Line

The code would be: **L P V I U C**

- L: Loan
- P: Consumer/Personal
- V: Variable Rate
- I: Interest Only (common for lines of credit)
- U: Unsecured
- C: Cash Settlement

### Why use this model?

Financial institutions use these codes because they are "machine-readable." If a bank has 10,000 different loans, they don't want to read 10,000 PDF contracts to find out which ones have floating interest rates. They can just filter their database for any code where the **3rd character is "V"**.

## Loans Ontology in a PMS

Gemini said
In a professional Portfolio Management System (PMS) or banking core, modeling a loan is significantly more complex than modeling a stock or a bond. Because a loan is a private contract, you have to "digitize" the legal terms of a 50-page document into a structured data set.

A loan is typically modeled using a three-tier hierarchy:

### 1. The Facility Level (The "Parent")

This is the master agreement between the lender and the borrower. It defines the "envelope" of the deal.

- **Total Commitment**: The maximum amount the borrower can ever take (e.g., $100M).
- **Availability Period**: The window of time during which the borrower can ask for money.
- **Covenants**: The legal rules (e.g., "The borrower must maintain a Debt-to-Equity ratio of 2:1").

### 2. The Tranche/Loan Level (The "Child")

Within a single facility, there might be different "slices" with different rules.

- **Term Loan A**: A standard loan that is paid back over 5 years.
- **Term Loan B**: A loan that is paid back all at once at the end (Balloon).
- **Revolver**: A line of credit that can be borrowed, repaid, and borrowed again.

### 3. The Components (The "Data DNA")

To make the loan "run" in a system, you must model these four specific data blocks:

#### A. The Amortization Schedule

- **Bullet**: 0% principal paid until the final date
- **Linear/Level**: Equal principal payments every month.
- **Annuity**: Fixed total payments (like a home mortgage) where the interest portion shrinks over time.

#### B. The Interest Engine

Unlike bonds, which usually have fixed coupons, most institutional loans are **Floating**.

- **Base Rate**: (e.g., SOFR, EURIBOR, or Prime Rate).
- **Spread/Margin**: The "plus" (e.g., SOFR + 2%).
- **Day Count Convention**: How the system calculates daily interest (e.g., Act/360 or 30/360). This can change the interest owed by thousands of dollars on large loans.

#### C. The Fee Structure

Loans involve more fees than securities.

- **Commitment Fee**: A fee charged on the unused portion of a Revolver.
- **Utilization Fee**: A fee charged only if the borrower uses more than, say, 50% of the loan.
- **Upfront Fees**: Fees paid at the moment the loan is signed.

#### D. The Lifecycle Events

Your model must be able to handle "state changes" over time:

- **Drawdown**: When the borrower takes cash.
- **Paydown**: When the borrower returns cash.
- **Capitalization**: When interest is added to the principal (PIK) instead of being paid in cash.

### The Data Model Summary

| Object | Attribute Examples |
| :--- | :--- |
| **Counterparty** | Legal Entity Identifier (LEI), Credit Rating, Country. |
| **Schedule** | Frequency (Monthly/Quarterly), Holiday Calendar (e.g., NY Banking Days). |
| **Rates** | Reset Frequency, Floor/Cap (the minimum/maximum interest allowed). |
| **Collateral** | Asset Type (Real Estate, Inventory), Loan-to-Value (LTV) ratio. |

