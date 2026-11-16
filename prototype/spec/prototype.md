# POC-BOOKING: booking proof of concept

Version: **0.1.1**. Status: **approved for the local prototype**.

Contract: **POC-BOOKING-API v0.1.1**, approved in section 6.

The user explicitly approved DEC-P01–DEC-P08 and all seven review amendments on 2026-11-16, and instructed the implementer to record approval of the resulting v0.1.1 specification and contract. Evidence: `approval-v0.1.1.md`. This approval applies only to the local proof of concept; it is not teacher approval and does not approve the original project's draft payment, notification, or mobile requirements. Prototype extensions remain distinguished from original project facts below.

## 1. Purpose, original facts, and prototype boundary

**Demonstration question:** Can a client with an active membership reserve a place in a training, see the reservation, and cancel it, while the system prevents overbooking and unauthorized access?

The business problem is manual reception work and inconvenient access to reservations. The original project connects booking to the goal of simplifying reservations and reception work (G-47 in the project PDF). Its R-02 covers creating/cancelling a reservation, C-60 limits reservations to an available training within capacity, C-39 restricts access, and I-06 requires an active membership. Source: project PDF pp. 2 and 15-18.

The demonstrable slice is:

> Klient -> Spracovanie rezervácie / Rezervácia tréningu -> Správa rezervácií -> Modul rezervácií -> membership and schedule/capacity checks -> persisted confirmed reservation -> visible result.

Names come from the source PDF and referenced diagrams. Some exports group membership and reservation responsibilities; this prototype keeps those responsibilities distinct inside one application. Do not invent EA element IDs for visible names or pretend the exported diagrams define URLs, database columns, or race-handling algorithms.

### Included

- A real runnable local browser application with a Slovak UI.
- Login/logout using fictional seeded accounts; authenticated server-side access checks.
- Seeded users, memberships, trainers, activities, rooms, trainings, and reservations.
- A schedule showing training details, capacity, occupied/free places, and the current client's booking state.
- Create a reservation with active-membership, time, duplicate, and capacity checks.
- A list of the current client's reservations; cancellation of an owned reservation.
- Persistence across browser reloads and application restarts.
- Automated tests, a repeatable demo, and recorded verification evidence.

### Excluded

- Public registration, password recovery, account/profile editing, and staff administration screens.
- Trainer/room/activity CRUD, editing the schedule, or a trainer participant-list feature.
- Purchasing, activating, renewing, or paying for memberships; cash-payment confirmation; real or mock payment gateways.
- Email/push notifications or a notification-delivery subsystem. Show the booking result in the application.
- Native mobile apps, public deployment, cloud infrastructure, microservices, background jobs, production operations, and enterprise audit/reporting.

This is partial support for R-02 and access-related R-07, with seeded supporting data for R-03/R-04/R-05. It is not completion of all those requirements. In particular, original AC-02-1 also mentions R-06 notification delivery: the prototype's on-screen confirmation does not satisfy that excluded production subcase.

## 2. Approved decisions for this prototype

| ID | Approved prototype decision | Consequence |
| --- | --- | --- |
| DEC-P01 | Local Python web application with FastAPI, Jinja2, SQLite, and minimal JavaScript; one process and one local database. | No separate SPA, native app, cloud, broker, or real provider credentials. The user's earlier Python estimation choice is context, not proof this implementation choice was already approved. |
| DEC-P02 | Use seeded accounts and memberships; no registration or payment-driven activation. | Login and access controls are real; membership acquisition is explicitly not implemented. |
| DEC-P03 | A client must have an effective active membership when booking, checked with fresh server time inside the write transaction immediately before the mutation is committed. | Require stored status `active` and `valid_from <= now < valid_until`. Before `valid_from`, effective state is `pending`; at/after `valid_until`, it is `expired`; otherwise stored pending/expired states remain ineligible. No additional requirement to remain active until the training date. |
| DEC-P04 | Reserve/cancel only before the training start; at most one confirmed reservation per client/training; cancelled reservations can be rebooked. | These are prototype extensions, not rules already specified in the original R-02 text. No booking fees, cancellation windows, refunds, or penalties. |
| DEC-P05 | Creation and cancellation are synchronous; authorization, availability checks, and the booking write must remain consistent under concurrency. | Duplicate creation returns a conflict without a second booking; repeated cancellation is a successful no-op. No asynchronous event system or generic idempotency platform. |
| DEC-P06 | Use authenticated sessions; identity and role come from server-trusted state. Protect state-changing browser requests against CSRF. | Keep the original C-01 client-ID field but reject a mismatch with the authenticated client. Do not authenticate from that field. |
| DEC-P07 | UTC-aware timestamps internally; display dates/times in `Europe/Bratislava`; Slovak UI. | Seed dates relative to an explicit seed timestamp; restart does not silently move trainings. Boundary tests use a controlled clock. |
| DEC-P08 | Local demo data can be initialized and explicitly reset by a command; server binds to loopback by default. | No automatic destructive reset on startup and no public deployment. Initialization must not overwrite a populated database. |

Approval of this prototype does not modify the original project PDF, ADRs, or enterprise architecture baseline. A simple decision table is sufficient here; do not create eight separate ADR documents.

## 3. Actors, data responsibilities, and allowed interactions

### Actors and permissions

| Actor | Allowed in the prototype | Not allowed |
| --- | --- | --- |
| Unauthenticated visitor | Open login page; attempt login. | Read protected schedule/account/reservation data or perform reservation mutations. |
| Authenticated client | View schedule, own effective membership state, own reservation history; book/cancel under the stated rules. | See another client's reservations or mutate another client's booking; change accounts, memberships, schedule, or roles. |
| Seeded trainer account | Login/logout, read the schedule through `GET /trainings` and its browser page, and see an explanation that staff management is outside this demo. | Use client-only membership or reservation operations. No trainer dashboard or participant list is required. |

Cancellation requires ownership, not an active membership. A client whose membership expired after booking may still cancel an owned future reservation. Creating a new booking still requires active membership.

### Logical responsibilities

| Existing responsibility | Prototype realization | Owns / provides |
| --- | --- | --- |
| Client portal | Templates, browser interactions, HTTP adapters | Display and input handling; no independent business decisions. |
| Users / permissions | Small authentication/access module | Users, password hashes, trusted identity/role, sessions and permission checks. |
| Membership module | Read-only membership service plus seed data | Membership meaning and effective validity check. No activation lifecycle implementation. |
| Schedule / capacity module | Read-only schedule service plus seed data | Training times, room/activity/trainer information and configured capacity. |
| Reservations module | Booking/cancellation service | Reservation writes, duplicate prevention, ownership, and confirmed occupancy query. |
| Storage service | SQLite adapter | Durable reads/writes and transaction boundaries; no separate deployable service. |

The client portal calls the application services. Reservation processing uses the membership validity service and schedule information, and queries confirmed reservations for occupancy. It must not change membership or training data. Read views may join these data for display. A shared SQLite transaction is allowed to enforce the booking invariant: logical ownership does not imply separate databases or network services.

Basic concepts: User, Membership, Training, Reservation, Activity, Trainer, and Room. A training has one time interval, capacity, and references to its activity, trainer, and room. A reservation links one client to one training. Do not create a separate persistent copy of a reservation confirmation.

Reservation transitions implemented in the demo are creation as `confirmed` and `confirmed -> cancelled`. Cancellation preserves the record. Rebooking creates a new reservation ID; cancellation of an old cancelled ID must not affect any newer booking. Past confirmed records remain history and are labelled as past. The original `created`/`completed` lifecycle is not fully implemented; do not claim a background completion mechanism exists. There is no bulk deletion or reservation editing flow.

Physical schema, indexes, transactions, and compatible implementation libraries may be chosen by the developer within these boundaries. A working persistent application necessarily needs a schema; no additional ERD/UML documentation assignment is required by this adapted package.

## 4. Rules and quality expectations

| Rule | Required observable behavior | Original source or proposed extension |
| --- | --- | --- |
| BR-P01 | Confirmed reservation count never exceeds training capacity, including competing requests. | Original I-01 / I-04 / C-60; atomic behavior is DEC-P05. |
| BR-P02 | Only an authenticated client can create a reservation; supplied client ID must equal trusted identity. | Original C-39 / I-05; session and mismatch handling are DEC-P06. |
| BR-P03 | Only the owner sees the booking in their list and can cancel it. | Original C-39 / I-05, detailed here. |
| BR-P04 | A new booking requires effective active membership at commit time; absent/pending/expired is rejected. | Original I-06, temporal details DEC-P03. |
| BR-P05 | At most one `confirmed` reservation exists per client/training; a repeated create while it exists never consumes another place. After cancellation a delayed POST replay can create a new reservation, subject to all current rules. | DEC-P04 / DEC-P05; accepted replay limitation. |
| BR-P06 | Only `confirmed` reservations consume capacity. Cancellation releases one place exactly once. | Original reservation meaning; repeat details DEC-P05. |
| BR-P07 | A training with `starts_at <= now` cannot be newly booked or first cancelled. | DEC-P04. |
| BR-P08 | Rebooking after cancellation is allowed if all current booking rules pass. | DEC-P04. |
| BR-P09 | Failed validation, denial, storage failure, or a losing concurrent request does not leave a partial booking. | Prototype consistency requirement supporting I-01 / I-05 / I-06. |

For two active clients contesting one remaining place, exactly one confirmed reservation is committed. The losing valid request observes the full training and receives `409 capacity_full`; a transient database-lock implementation exception is not an acceptable substitute for this ordinary business outcome. Use a suitable transaction/retry strategy bounded to the local application. Do not fake this by disabling buttons or serializing only a single browser's clicks.

After acquiring the write lock, and after any lock wait or transaction retry, sample fresh UTC server time for membership/training checks immediately before writing and committing. Request-arrival time must not authorize a mutation after a validity/start boundary. Keep dependent reads and writes in the same transaction. Test both lock-wait and retry boundary cases, same-client contention, and concurrent cancellation.

Use parameterized database access, password hashing, protected sessions, and minimal disclosed user data. Local development cookies may work over loopback HTTP; do not represent that as a production security configuration. The browser must never receive password hashes, other clients' contact information, or database exceptions.

Do not put personal data or secrets in logs. There is no separate production audit-log requirement for this slice. State the absence of comprehensive audit/history tooling as a prototype limitation.

The source PDF mentions confirmation within two seconds at normal load, but does not define that load. Record a local functional smoke measurement if feasible. Do not claim a formal performance/SLA pass from that measurement or from a unit-test duration.

## 5. Screens and demo data

### Screens

1. **Prihlásenie**: username/password form, readable invalid-credentials message, fictional demo-account information.
2. **Rozvrh tréningov**: activity, trainer display name, room, local start/end time, capacity, occupied/free places, current membership badge, and reservation action/result. Use clear states such as available, full, already reserved, membership required, and started.
3. **Moje rezervácie**: only the current client's records; training details; confirmed/cancelled state; cancel action for owned future confirmed bookings. Empty state and server failure state must be readable.
4. **Staff out-of-scope notice** for the trainer demo account; not a staff-management screen.

Common navigation shows the signed-in account and logout. Use a simple polished layout, readable labels, keyboard-accessible forms, and a phone-width layout without horizontal overflow. There is no existing frontend theme to preserve in this workspace. The implementer can choose understated colours and layout without asking for a design system.

Buttons must show progress and recover after an error. After a rejected or uncertain request, reload server-authoritative booking/availability data. Never automatically retry a booking POST, including after a lost response; reconcile first. If reconciliation fails, block further booking submissions until a successful refresh. Never show success until the server confirms persistence. Disabling a button is usability, not the capacity/access check.

### Fictional seed accounts

| Username | Role | Membership | Purpose |
| --- | --- | --- | --- |
| `anna` | client | Active now | Happy path and cancellation. |
| `boris` | client | Active now | Competing booking, existing reservation, ownership separation. |
| `cyril` | client | Expired | Membership denial and ability to cancel an earlier owned future booking. |
| `dana` | client | Pending | Pending-membership denial. |
| `trener` | trainer | None | Client-operation role denial. |

One documented fictional password, for example `Demo123!`, can be shared by these local seed accounts. Store hashes, not plaintext passwords. These are demo credentials, not production account defaults. Registration is not needed to exercise the rules.

Seed active memberships so they overlap now but there is never more than one active membership per client (original I-02). Memberships are pre-existing fixtures; do not create fake settled payments or claim the original activation-after-payment lifecycle was executed.

### Training fixtures

- A future training with capacity 3 and one confirmed booking owned by Boris: free places 2.
- A different future training with capacity 1 and no reservations: the last-seat race fixture for Anna and Boris.
- A future training with capacity 1 already reserved by Boris: full-training denial for Anna.
- A training that has already started: time-boundary denial. It can be shown in a clearly labelled past section.
- A different future training with capacity 2 and an existing confirmed reservation owned by Cyril, representing a reservation made before his membership expired. He may cancel it.

Use a fixed saved seed timestamp and relative future dates, e.g. one to seven days later. Initialize only an empty demo database; repeating initialization leaves current data unchanged. An explicit `--reset-demo` command recreates only this application's documented local demo database. Tests use separate temporary databases and a controlled clock, never the user's demo database.

## 6. Approved API contract

**Contract ID: POC-BOOKING-API. Version: 0.1.1. Status: approved for the local prototype.**

This small HTTP contract is the normative external behavior approved for the prototype. Python modules remain internal calls, not separate services. Generate FastAPI's OpenAPI description as a useful implementation artifact, but validate the implementation against this reviewed specification; generated OpenAPI alone cannot prove conformity.

The original C-01 example specifies `POST /reservations`, `id_klienta`, `id_treningu`, a response containing `id_rezervacie` and `stav: confirmed`, and errors `409 capacity_full` and `401 unauthorized`. Keep those names and meaning. The `201` success code, additional errors, error shape, read/cancel routes, login/session mechanism, ownership and repeat behavior below are **approved prototype refinements**, not original project facts or teacher-approved additions.

### Common policy

- Same-origin browser UI and HTTP API; session authentication for protected operations.
- All state-changing calls carry a server-issued CSRF token. The implementation chooses a standard compatible session/token mechanism and documents it. It must reject a missing/invalid token with `403 csrf_invalid` without mutation, including login/logout where applicable.
- Login UI can obtain a token before authentication. `GET /session` returns `200` with `user: null` and `csrf_token` when logged out, or a minimal user summary and token when logged in; it exposes no membership/reservation data when logged out.
- Timestamps use RFC 3339 UTC in JSON. Display conversion is a UI concern.
- IDs are positive integers. Missing/invalid fields use FastAPI's documented `422` validation response. Application errors use `{"error":{"code":"...","message":"..."}}`; the UI maps codes to Slovak text.
- Except the documented session/login and health endpoints, protected API calls return `401 unauthorized` without a valid session. Client-only operations return `403 forbidden` for the trainer role.
- Error precedence: on protected routes, authenticate first (`401`), then check the allowed role (`403 forbidden`) and, on mutations, CSRF (`403 csrf_invalid`), then validate input (`422`), then apply business checks in the order below. Invalid JSON or path IDs must not bypass this precedence. Login/logout check CSRF before input validation; they allow anonymous sessions as documented.
- An absent or other-client reservation ID returns `404 reservation_not_found`, so cancellation does not reveal another client's booking details.
- Unexpected persistence failure: rollback, return `503 storage_unavailable` when identifiable as unavailable storage (otherwise sanitized `500 internal_error`), show a retry message, and never fall back to a fake successful in-memory write.

### Operations

| Operation | Request | Successful response | Refusals / notes |
| --- | --- | --- | --- |
| `GET /health` | None | `200 {"status":"ok"}` if the application and storage are usable. | `503` if storage is unavailable; no sensitive configuration. |
| `GET /session` | Optional session cookie | `200 {"user":null,"csrf_token":"..."}` or `user:{id,username,role}`, with token. | No sensitive user fields. Used to establish trusted identity in the UI. |
| `POST /login` | JSON `{username,password}` and CSRF token | `200 {"user":{id,username,role},"csrf_token":"..."}`; establish/refresh session. | `401 invalid_credentials`; do not reveal whether username exists. |
| `POST /logout` | CSRF token; session optional | `204`; clear session. | Repeated logout with a valid current anonymous CSRF context is harmless. |
| `GET /trainings` | Authenticated account | `200 {"items":[TrainingView...]}` | Reads schedule only; no other clients' identities. Trainer may read this public-to-authenticated summary. |
| `GET /memberships/current` | Authenticated client | `200 {"membership":MembershipView}` or `{"membership":null}` | Client's own state only; no mutation. |
| `GET /reservations` | Authenticated client | `200 {"items":[ReservationView...]}` | Server scopes to current client, including cancelled history. No client-ID override or all-clients mode. |
| `POST /reservations` | Authenticated client; JSON `{id_klienta,id_treningu}` | `201 {"id_rezervacie":integer,"stav":"confirmed"}` | `403 client_mismatch`; `404 training_not_found`; `409 training_started`; `409 duplicate_reservation`; `403 membership_inactive`; `409 capacity_full`. |
| `DELETE /reservations/{id_rezervacie}` | Authenticated client; no body | `200 {"id_rezervacie":integer,"stav":"cancelled"}` | `404 reservation_not_found`; `409 training_started` on first cancellation; no active-membership requirement. Already cancelled owned reservation returns the same successful state without another release. |

Suggested HTML routes: `GET /login`, `GET /schedule`, `GET /my-reservations`, and a small trainer notice page. An unauthenticated HTML request redirects to login; this does not change the JSON API's `401` policy. HTML names and layout are implementation details; the API routes above are the contract.

### Read models

- `TrainingView`: `id_treningu`, `aktivita`, `trener`, `priestor`, `starts_at`, `ends_at`, `kapacita`, `obsadene`, `volne_miesta`, `moja_rezervacia_id` (nullable). The final field contains only the current client's confirmed reservation ID and is null for the trainer. Do not include a participant list.
- `MembershipView`: `id_clenstva`, `typ`, `stav` (effective `active`, `pending`, or `expired`), `valid_from`, `valid_until`. Return null if no membership exists. Effective state is `pending` before `valid_from`, `expired` at/after `valid_until`, and otherwise the stored state. Only effective `active` permits booking. Seed fixtures contain at most one membership record per client; no membership lifecycle writes are exposed.
- `ReservationView`: `id_rezervacie`, `id_treningu`, `stav` (`confirmed` or `cancelled`), `created_at`, nullable `cancelled_at`, and a `training` object with the training fields needed for display. Do not embed other clients' bookings.

### Deterministic processing and repeats

For create: authenticate, check client role and CSRF, validate field types, reject a mismatched client ID, then within the write transaction check training existence, reject an already-started training, reject an existing confirmed duplicate, require effective active membership, then check capacity and commit. Use fresh server time after lock waits/retries immediately before mutation/commit. This ordering makes a repeated future creation return `duplicate_reservation` even when the first booking used the last place or membership subsequently expired. At/after training start, `training_started` wins over duplicate/membership/capacity errors.

For cancel: authenticate, check client role and CSRF, validate the positive path ID, then obtain an owned reservation inside the write transaction (otherwise 404), return existing cancelled state if already cancelled, otherwise reject a started training using fresh server time after lock waits/retries, then atomically mark cancelled and commit. A repeat after the training starts still returns the already-cancelled state. Cancellation does not require active membership. A concurrent create/cancel must not corrupt the confirmed count; cancellation always targets its exact reservation ID.

No `Idempotency-Key` system is required. Creation is duplicate-safe while a confirmed booking exists, but is not transport/response-idempotent: a first success is 201 and a replay while future and confirmed is 409. Once cancelled, a delayed replay is indistinguishable from intentional rebooking and may return 201 with a new ID. This limitation is explicitly accepted. The UI never automatically retries booking POSTs; after an uncertain result it refreshes own reservations and availability before permitting another submission. An old cancellation replay is a successful no-op and cannot cancel the new ID.

## 7. Acceptance scenarios and traceability

These are approved executable acceptance examples for v0.1.1. IDs are local to the prototype. Each row is a compact Given / When / Then; tests may use pytest rather than requiring a separate BDD framework.

| Scenario | Given / When / Then | Trace |
| --- | --- | --- |
| SC-P01 | Given valid Anna credentials, when she logs in, then her session is established; wrong credentials fail without protected data. | R-07 subset; BR-P02; login/session. |
| SC-P02 | Given an authenticated client or trainer, when the schedule is read, then capacity and free places reflect confirmed reservations, with no other-client identities; a trainer sees no own reservation ID or client-only actions. | R-02 support; BR-P01 / BR-P03; trainings. |
| SC-P03 | Given an active client, a future training and capacity, when the client books, then exactly one confirmed reservation is persisted and free places decrease by one. | R-02; I-01 / I-06; C-01 refinement; create. |
| SC-P04 | Given a full training, when a different active client books, then `409 capacity_full` is returned and records/capacity do not change. | C-60 / I-01; create. |
| SC-P05 | Given absent, pending, expired or not-yet-valid membership, when the client books a future available training, then `403 membership_inactive` is returned and no reservation is created. Before valid_from the read state is pending; valid_from is inclusive and valid_until exclusive. Membership need not cover the training date. | I-06; BR-P04 / DEC-P03; separate fixtures and controlled clock. |
| SC-P06 | Given an existing confirmed future booking, when that client submits create again, then `409 duplicate_reservation` is returned and there remains exactly one confirmed booking, including a full training and subsequently expired membership. After training start return training_started instead. | BR-P05; create/replay and precedence. |
| SC-P07 | Given an owned future confirmed booking, when the client cancels, then it remains in history as cancelled and exactly one place becomes free. | R-02; BR-P06; cancel/list. |
| SC-P08 | Given an owned cancelled booking, when cancellation is repeated, then the cancelled state is returned and availability does not change again. | BR-P06; cancel/replay. Include a repeat after the training has started. |
| SC-P09 | Given an owned cancelled booking and valid current eligibility/capacity, when the client books again (including an indistinguishable delayed POST replay), then a new ID is created and exactly one confirmed booking exists. Repeating cancellation of the old ID cannot affect the new booking. | BR-P08; accepted POST replay limitation; ID-scoped cancellation. |
| SC-P10 | Given Anna and Boris with distinct bookings, when Anna lists reservations or attempts to cancel Boris's ID, then Boris's record is absent from her list and cancellation returns 404 without mutation. | C-39 / I-05; BR-P03; list/cancel. |
| SC-P11 | Given Anna's valid session, when create contains Boris's client ID, then `403 client_mismatch` is returned without booking for either client. | C-39 / I-05; BR-P02; C-01 refinement. |
| SC-P12 | Given no authenticated session, when protected APIs are called, then 401 is returned even with invalid input/CSRF; given the trainer session, client-only membership/reservation operations return 403 before CSRF/input validation, while schedule reads succeed. | C-39 / I-05; BR-P02 / BR-P03; approved precedence. |
| SC-P13 | Given a training at or past its start, when a new booking or first cancellation is attempted, then `409 training_started` is returned with no mutation. | BR-P07; DEC-P04. Include exact-boundary tests. |
| SC-P14 | Given two active clients and exactly one free place, when they book concurrently using independent requests/connections, then one request succeeds, the other receives capacity_full, and the final confirmed count equals capacity. Also exercise same-client concurrent create, concurrent cancellation, and membership/start boundaries crossed during lock waits or retries using fresh server time. | I-01; BR-P01 / BR-P09; real contention, not a serial loop. |
| SC-P15 | Given a confirmed reservation, when the app and connection are restarted using the same database, then that reservation and availability remain correct. | R-02 persistence; SQLite adapter. |
| SC-P16 | Given a valid client session, when a mutation has invalid CSRF and invalid input, then 403 csrf_invalid wins; with valid CSRF, invalid input returns 422. Login/logout also enforce CSRF. No rejected request changes state. | DEC-P06; BR-P09; authentication, role/CSRF, validation precedence. |
| SC-P17 | Given an owned future booking made while membership was active, when membership is now expired and the client cancels, then cancellation succeeds; a new booking still fails. | BR-P03 / BR-P04; approved prototype cancellation policy. |
| SC-P18 | Given an injected storage failure, when a booking mutation cannot complete, then the response is a sanitized failure and no partial/fictional booking is returned. | BR-P09; rollback/error policy. |
| SC-P19 | Given an initialized database with a new user booking, when initialization runs again, then it preserves that booking; an explicit demo reset restores only the documented fixtures. | DEC-P08; seed/reset. Test on temporary files. |
| SC-P20 | Given a running app, when the five-minute walkthrough is performed through the browser, then login, schedule, booking, visible error, own-list cancellation, and logout work at desktop and phone-width layouts. An uncertain booking result triggers reconciliation without another POST; failed reconciliation blocks booking until refreshed. Past records are labelled without a completion transition. | End-to-end UI; mark UNKNOWN if no browser verification was possible. |

The validation report maps each SC-P ID to an actual test name or a recorded manual check, plus PASS / FAIL / UNKNOWN. Include evidence for unknown training/reservation IDs, membership validity boundaries, and two simultaneous requests by the same client so the duplicate invariant is not protected only in sequential tests.

## 8. Implementation plan and definition of done

Use three small implementation steps after approval, without three new approval gates:

1. **Foundation**: dependency setup, persistent storage, deterministic fixtures, login/session, read-only schedule and membership.
2. **Booking**: create/list/cancel services and routes, permissions, time rules, transaction behavior, and meaningful automated tests.
3. **Demonstration**: rendered UI, error/reload behavior, seed/reset instructions, browser smoke check, traceability and validation report.

Choose a currently supported Python version compatible with the tools available on the user's Windows machine, and record the actual tested version. Resolve a small compatible dependency set and record it in `requirements.txt`. Use a local virtual environment. Dependency versions and internal schema design are delegated implementation choices, not new business questions.

The final README must provide actual PowerShell commands for creating the environment, installing dependencies, seeding an empty database, starting on `127.0.0.1`, testing, and explicitly resetting demo data. Do not require an undisclosed API key, a database server installation, or a separate Node build.

Done means:

- A clean checkout can be installed, seeded and started using the documented commands.
- Real requests and rendered pages execute the confirmed contract and rules against persistent storage.
- Core acceptance tests pass, including authorization, ownership, membership boundaries, replay handling, and the final-seat race. Relevant unperformed manual checks are honestly recorded.
- Existing project source files remain unchanged.
- README documents fictional credentials, tested versions, shortcuts, and limitations.
- `DEMO.md` provides a repeatable five-minute script using the fixtures, with reset instructions and expected outcomes.
- `reports/validation.md` contains commands, actual results, scenario-to-test mapping, and full/partial/seed-only coverage of original requirements.
- The implementation does not claim production authentication, payment integration, notification delivery, native mobile support, performance certification, or completion of the original full product.

## 9. Known source gaps and how this slice avoids them

| Gap / ambiguity in original materials | Approved prototype treatment |
| --- | --- |
| Gap A leaves cash payment at reception; the membership lifecycle links activation to confirmed payment. | Memberships are pre-existing seed fixtures. No new activation or cash-confirmation rule is invented. |
| C-01 gives only a short request/response/error example, with no exact duplicate, ownership or retry policy. | Section 6 records the explicitly user-approved prototype extensions; original 401/409 errors remain attributed to C-01. |
| Detailed authentication technology is not selected in the original project. | DEC-P01 / DEC-P06 approve local sessions and basic safeguards for this POC. |
| Full R-06 / R-08 are draft and outside the selected slice. | No email/push or native mobile work. Responsive web layout is not claimed as completion of R-08. |
| Exact current EA baseline label and human export verification record are absent. | Manifest records this honestly. Reuse the supplied views; request human clarification only if a material diagram/source contradiction affects this slice. |
| The teacher's full workflow uses multiple artifact files and review roles. | This is a compact adaptation with one specification/contract review and one evidence-based implementation handoff; it does not claim strict v4 certification. |

## 10. Source map

See the manifest for exact paths. The project PDF and EA PNGs supply the original context and requirements. The GAP PDF supplies iteration context. The teacher's framework/template/rules supply methodological guidance, not domain behavior.

The approved prototype Python stack is supported by official documentation for [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), and [Python SQLite](https://docs.python.org/3/library/sqlite3.html). These references do not select project business rules or imply production readiness.

Teacher references were available and read on 2026-11-16: framework pp. 2–3, 8–9, 12–15, 18; AI rules pp. 1–7; project template pp. 1–5, 12–16. Their useful guidance is retained through this compact package, explicit human approval, existing architecture exports, and scenario-to-test evidence. The user's approved adaptation does not require copying example roles, directory trees, technologies, UML assignments or unrelated examples. It does not claim teacher approval, verified EA baseline certification or strict v4 compliance.
