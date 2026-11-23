# INC-01 · Client account decision and interface

**2026-11-23 · IMPLEMENT_CHANGE · Local course project**

Booking baseline [POC-BOOKING and POC-BOOKING-API v0.1.1](prototype.md). The [INC-01 preparation draft](drafts/increment-01-client-registration.md) gives detailed rules and scenarios. [Validation](../reports/validation-inc-01.md) records the observed results.

## DEC-C08 user decision

The user confirmed DEC-C08 and explicitly authorized IMPLEMENT_CHANGE for INC-01. A visitor signs up with a username, password and display name. The server assigns the Client role. The client signs in manually, can view the schedule and can edit their own display name. Signup creates the account only. Booking requires an effective active membership.

The original project PDF, p. 18, describes a waiting membership after registration. The local INC-01 decision creates no membership row, so the existing `GET /memberships/current` returns `{"membership":null}` and a valid booking attempt for a future available training receives `403 membership_inactive`. The project PDF and the historical v0.1.1 approval retain their original scope. Later account and staff decisions are recorded in the [INC-02 contract](drafts/increment-02-account-administration-http-v0.1.0.md).

## Delivered HTTP interface v0.1.0

The user confirmed behavior and authorized implementation directly. The route names and response details below describe INC-01 at delivery, when the live and generated OpenAPI both described POC-BOOKING-API v0.1.1. INC-02 adds session roles and account administration to the live schema.

| Operation | Input and outcome | Trace |
| --- | --- | --- |
| `GET /register` | Public Slovak signup page. Signed-in clients redirect to `/schedule`, staff to `/staff` (303). Successful signup offers the login link. | R-01, client portal, SC-C01/09. |
| `POST /api/account/registration` | JSON `{username,password,display_name}` and `X-CSRF-Token` from anonymous `GET /session`. Returns `201 {"username": "..."}` and keeps the session anonymous. A signed-in caller gets `403 already_signed_in`, a missing or invalid token gets `403 csrf_invalid`, invalid input gets sanitized `422 validation`, and an existing username gets `409 username_taken`, in that order. | R-01, users and permissions, account, BR-C01/02/04/05, SC-C01/03/04/06/07. |
| `GET /profile` | Slovak own-profile page. Unauthenticated requests redirect to `/login`, staff to `/staff` (303). | R-01, R-07, client portal, SC-C05/09. |
| `GET /api/account/profile` | Client session required. Returns `200 {id,username,role,display_name}`. Legacy accounts display their username until they save a name. | R-07, users and permissions, own account, BR-C03/06, SC-C02/05/08. |
| `PUT /api/account/profile` | Client session and CSRF token required. JSON contains only `display_name`. Returns the updated profile with status 200. Repeating the same value has the same visible effect. | R-01, R-07, users and permissions, own account, BR-C03/05, SC-C02/04/05/07. |

Profile identity comes from the authenticated session. Profile API errors follow authentication (401), role (403), CSRF for writes (403), then validation (422). The new endpoints return errors as `{"error":{"code":"...","message":"..."}}`. Database errors are sanitized and transactional writes roll back on failure. New usernames use 3–32 lowercase ASCII letters, digits, periods, underscores or hyphens and start with a letter or digit. Signup checks duplicates using SQLite's case-insensitive ASCII comparison. Display names are trimmed to 1–80 characters and disallow control characters. Passwords are 12–128 characters and are hashed as supplied. Rejected requests do not echo submitted values. A lost signup response offers manual sign-in and sends no automatic retry.

The explicit `python -m app.migrate` command upgrades the local SQLite schema from 0.1.1 to 0.2.0 in place. IDs, passwords, roles, sessions, memberships and bookings are preserved. Executing it again reports that the database is current. Fresh seeds use schema 0.2.0.
