# Backend Components

The backend is composed from two domain components.

## Custodian Component

Package: `backend.app.custodian`

Purpose: simulate an OpenWealth-style custodian provider that exposes source data.

- Router: `backend.app.custodian.router`
- Schemas: `backend.app.custodian.schemas`
- Service: `backend.app.custodian.service`
- API tag: `custodian`
- Routes: `/custody/customers`, `/custody/customers/{customer_id}/accounts`, `/custody/customers/{customer_id}/positions`, `/custody/customers/{customer_id}/transactions`, `/custody/customers/{customer_id}/snapshot`

## Profile Component

Package: `backend.app.profile`

Purpose: own advisory profiling, questionnaires, client segment configuration, suitability, and audit-backed processing.

- Router: `backend.app.profile.router`
- Existing services: `backend.app.services.admin`, `backend.app.services.suitability`
- Existing schemas: `backend.app.schemas.admin`, `backend.app.schemas.suitability`
- API tag: `profile`
- Routes: `/admin/questionnaires`, `/admin/client-segments`, `/suitability`

## Composition Root

Package: `backend.app.main`

Purpose: create the FastAPI app, configure middleware, attach cross-cutting dependencies, and include component routers.

The composition root should stay thin. Domain endpoints should live in component routers.
