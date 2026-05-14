# OpenWealth Custody Simulation

This lab treats a custodian as a base data provider. The simulated provider follows the public OpenWealth custody shape: customers, accounts, positions, and transactions.

## Source Boundary

OpenWealth custody data should stay separate from advisory profile data.

- Custody source: customers, accounts, portfolios, positions, valuations, and transactions.
- Advisory profile: risk tolerance, knowledge, liquidity needs, objectives, restrictions, and suitability gates.
- Import snapshot: the bridge used by the lab to derive portfolio facts without overwriting questionnaire evidence.

## Public Reference Surface

The OpenWealth Association describes custody data as positions of any kind and transactions affecting position bookkeeping. SIX bLink Custody Services v3 exposes the relevant resource groups:

- `GET /customers`
- `GET /customers/:customerId/accounts`
- `GET /customers/:customerId/positions`
- `GET /customers/:customerId/transactions`

The lab mirrors those concepts with local endpoints under `/custody`.

## Lab Endpoints

- `GET /custody/customers`
- `GET /custody/customers/{customer_id}`
- `GET /custody/customers/{customer_id}/accounts`
- `GET /custody/customers/{customer_id}/positions`
- `GET /custody/customers/{customer_id}/positions?account_id=A-1001-CHF`
- `GET /custody/customers/{customer_id}/transactions`
- `GET /custody/customers/{customer_id}/snapshot`

The backend implementation lives in `backend.app.custodian`. The FastAPI app composes this as a separate router from the profile service, so custodian source data and advisory profile processing stay independent.

## Database Direction

The schema adds normalized custody tables:

- `advisory.custody_customer`
- `advisory.custody_portfolio`
- `advisory.custody_account`
- `advisory.custody_position`
- `advisory.custody_transaction`

Each table keeps a `raw_payload` JSONB column so future OpenWealth payloads can be preserved beside normalized fields. This is important for auditability and for comparing provider-specific extensions.

## Next Useful Increments

- Replace the in-memory provider with a repository reading from the custody tables.
- Add an import run table for source timestamp, correlation id, provider id, and ingestion status.
- Add portfolio-derived advisory signals: concentration, liquidity, currency exposure, single-position limits, and strategy drift.
- Add fixture generators for multiple custodian banks and inconsistent provider extensions.
