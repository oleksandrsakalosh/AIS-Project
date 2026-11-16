# Implementation plan: POC-BOOKING v0.1.1

Mode: IMPLEMENT_CHANGE. Approved contract: POC-BOOKING-API v0.1.1. Approval evidence: `../spec/approval-v0.1.1.md`.

The original R-02, C-39/C-60 and I-01/I-04/I-05/I-06 context and supplied architecture exports remain unchanged. The local prototype realizes booking, ownership and capacity rules, with fixture-only dependencies for membership and schedule. No payment, notification, account administration or native app work is introduced.

| Files | Responsibility and allowed dependencies |
| --- | --- |
| `app/db.py`, `app/schema.sql` | SQLite connections and transaction boundaries; durable storage. |
| `app/auth.py` | Password hashing, opaque protected sessions, CSRF; users and permissions. |
| `app/membership.py`, `app/schedule.py` | Read-only membership validity and schedule projections. |
| `app/booking.py` | Reservation writes, ownership and confirmed occupancy; calls membership and schedule using one transaction. |
| `app/main.py`, `app/models.py` | HTTP adapters, approved error precedence, sanitized errors and typed API contract. |
| `app/seed.py` | Explicit empty-database initialization/reset using fictional fixtures. |
| `app/templates/`, `app/static/` | Slovak UI; display/input only; no client-authoritative business decisions or automatic POST retries. |
| `tests/` | Acceptance/API/persistence/real-contention tests on temporary databases and controlled clocks. |
| `README.md`, `DEMO.md`, `reports/validation.md` | Actual tested setup/run/reset/test steps, walkthrough and scenario evidence. |

Implementation order: persistent foundation and authentication; transaction-backed booking and contract tests; rendered UI and browser checks; handover and recorded results. Physical schema, indexes and compatible dependencies are delegated implementation details under the approved adaptation. No extra UML/ERD or company template tree is required.
