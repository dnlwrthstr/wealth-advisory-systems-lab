# Money Market Instruments & Specifications

## 1. Overview
The Money Market is a sub-sector of the fixed-income market that deals in short-term debt financing. These instruments are characterized by high liquidity and maturities ranging from overnight to one year.

## 2. Primary Money Market Instruments
These instruments represent the core data entities within short-term funding markets.

| Instrument | Issuer | Description | Typical Maturity |
| :--- | :--- | :--- | :--- |
| **Treasury Bills (T-Bills)** | Government | Short-term debt sold at a discount; considered "risk-free". | 4 to 52 weeks |
| **Commercial Paper (CP)** | Corporations | Unsecured promissory notes used for payroll and inventory. | Up to 270 days |
| **Certificates of Deposit (CD)**| Banks | Time deposits with a fixed interest rate and maturity. | 1 month to 1 year |
| **Banker’s Acceptance (BA)** | Banks | A bank-guaranteed payment used in international trade. | 30 to 180 days |
| **Repurchase Agreement (Repo)**| Institutions | Selling securities with an agreement to buy them back later. | Overnight to 48h |

## 3. Technical Attributes for Money Market Data
If you are modeling these instruments in a database, these are the key fields required.

| Attribute | Data Type | Description |
| :--- | :--- | :--- |
| **Discount Rate** | Decimal | The rate used to determine the purchase price of T-Bills/CP. |
| **Face Value** | Decimal | The amount paid to the holder at maturity. |
| **Issue Date** | Date | The date the instrument was created and sold. |
| **Maturity Date** | Date | The date the principal and interest are settled. |
| **Day Count Basis** | String | Standard calculation method (e.g., `ACT/360` for US Money Markets). |

## 4. Market Comparison: Money Market vs. Capital Market
Understanding where these instruments sit in the broader financial landscape.

| Feature | Money Market | Capital Market (Bonds/Stocks) |
| :--- | :--- | :--- |
| **Duration** | Short-term ( < 1 year). | Long-term ( > 1 year). |
| **Risk Level** | Generally Low. | Variable (Moderate to High). |
| **Liquidity** | High (Easy to convert to cash). | Moderate (Depends on the asset). |
| **Purpose** | Liquidity & Working Capital. | Long-term Investment & Growth. |

## 5. Implementation Notes
* **Call vs. Notice Money:** Call money is settled within **24 hours**, whereas Notice money spans **2 to 14 days**.
* **Institutional Access:** While individuals can buy T-Bills, much of the money market (like Repos and Large CDs) is traded between institutional "counterparties".
* **Securitization:** Money Market Mutual Funds pool these assets to provide retail investors with diversified exposure.