# INC-01 · Client registration and own profile

The user confirmed DEC-C08 and authorized implementation for INC-01 on 2026-11-23. See the [decision record and delivered interface](../inc-01-client-account.md). The original preparation draft follows.

**Draft v0.1.0 · Proposed · PREPARE_SPEC · 2026-11-23.** Baseline: [POC-BOOKING and POC-BOOKING-API v0.1.1](../prototype.md). Business decision: [DEC-C08](course-project-preparation.md#decisions-for-the-user), pending user confirmation. The proposed interface is same-origin HTTP, with Slovak browser pages and the existing session mechanism. The exact HTTP contract follows in DESIGN_CONTRACT.

## Goal, actors and process

**G-47 → R-01 / US-01 (AC-01-1) → Registrácia klienta → client account usable on the web.** The project PDF pp. 2, 5 and 15–18 supplies the goal, service, registration requirement and access invariant. R-07 / C-39 / I-05 bounds profile access. GAP CP-01 also covers administration, which is scheduled in INC-02. Editing a display name is a local extension requested for the course project. The project identifies the product owner for R-01. User confirmation supplies approval for this proposed local interpretation.

As a prospective client, I want to create an account and sign in without calling reception. As a signed-in client, I want to see my username and update the name displayed in my profile.

1. A visitor opens the Slovak registration page from login and submits a username, display name and password. The browser uses a server-issued anonymous session and CSRF token.
2. The account service validates the request, assigns the client role and saves the account and profile together. The confirmation gives the user a clear link to sign in.
3. The new client signs in via the existing login path. The client sees the schedule, their empty reservation list, and an indication that they have no membership. The profile page displays their saved name and immutable username.
4. The client may save a revised display name. After reload, logout/login or application reopen, the latest committed name is visible.

The visitor and authenticated client are the principal actors. The seeded trainer checks compatibility and is denied client profile access. Administrator and reception provisioning, role administration, username/password changes, account recovery and external verification are deferred.

## Components, interactions and ownership

| Responsibility | Owns or consumes |
| --- | --- |
| **Klientsky portál** and same-origin HTTP adapter | Renders signup, login transition and own profile, sends input and renders safe field or operation errors. Consumes account/profile operations and the existing session/CSRF mechanism. |
| **Správa používateľov a údajov centra**, backed by the application responsibility for users and permissions | Owns persistent account identity, username, role and display name. Extends the existing authentication responsibility for signup and profile. The current auth service retains credentials, session lifecycle and trusted user context. Guards authorize via this context. |
| **Ukladanie údajov** | Supplies durable SQLite storage and atomic writes for account/profile data. Storage layout and migration mechanics are implementation choices. |
| **Modul členstiev**, **Modul rezervácií**, and **Modul rozvrhu a kapacít** | Retain their current data ownership. They continue to consume the trusted client ID. Signup and profile editing do not write a membership, reservation or training. |

Layered view 11 connects the registration process and user-data service. Views 03 and 17 identify authentication and access responsibility; view 08 shows client and membership as distinct business objects. The exports supply service boundaries. The local account/profile fields and transaction behavior are proposed here.

The runtime follows DEC-P01 and DEC-P08 with the existing local FastAPI/Jinja2 process, browser and SQLite data store. The proposed dependency is portal → users and permissions → storage. Signup and profile require no separate deployable component. DEC-P02's seed-only account scope is the one explicit extension proposed here.

## Rules and lifecycle

| Rule | Proposed observable behavior |
| --- | --- |
| **BR-C01 · Client creation** | Anonymous signup creates one active login account with an immutable user ID and server-assigned `client` role. The same saved username and password work through existing login. Signup preserves a logged-out session, with explicit login as the next action. A signed-in account already has an identity and gets a refusal if it attempts signup. |
| **BR-C02 · Valid and unique input** | New usernames use 3–32 lowercase ASCII letters, digits, period, underscore or hyphen with an alphanumeric first character. Match new usernames against existing names case-insensitively for uniqueness, including concurrent submissions. Require a trimmed display name of 1–80 characters with no control characters and an exact 12–128-character password. Treat passwords as entered, without trimming or normalization. Reject extra inputs such as role, user ID or membership. Existing usernames/passwords and login validation keep their v0.1.1 behavior. |
| **BR-C03 · Ownership and CSRF** | Only a signed-in client reads and updates their own profile. Resolve identity from the session. The only writable field here is display name. Enforce CSRF on both writes. Protected operations authenticate, check role, check CSRF for writes, then validate input and apply business rules. Signup uses the anonymous-session and CSRF boundary before input validation. |
| **BR-C04 · Registration is separate from membership** | A new client has no membership row and no membership or payment activity. `GET /memberships/current` returns `membership: null`. Attempting a valid new booking for an available future session yields the existing `403 membership_inactive`. This local decision differs from the waiting-after-registration example in the project PDF p. 18. |
| **BR-C05 · Durability and safe retries** | Save account and profile together. Hash each password with the existing scrypt mechanism and store only the necessary fields. On write failure, return a safe error and preserve prior state. Repeated signup for the same username cannot create a second account or replace the first password or profile. After an uncertain response, offer explicit sign-in and send no automatic signup replay. Repeating the same profile update has the same visible effect. |
| **BR-C06 · Compatibility** | Preserve stable IDs, current logins/sessions, roles, memberships, trainings and reservation history across an explicit upgrade. Existing seeded clients without a saved display name see their username as a fallback and can set a display name. Verify upgrading a disposable v0.1.1 database. |

Account lifecycle is **absent → registered with client role → eligible to sign in**. Browser authentication is a separate lifecycle (**anonymous → authenticated on login → anonymous on logout or expiry**), with v0.1.1 rotation and expiry. Profile data starts with the registered name (or username fallback for existing clients), and a valid update replaces only the display name. Membership lifecycle and reservation states are outside this increment.

Render validation and errors in Slovak and avoid disclosing credentials or internal errors in responses and logs. The screens must be usable with the keyboard and at desktop and phone widths. Use fictional accounts in evidence.

## Acceptance scenarios and evidence to collect

| ID | Given / When / Then | Trace and planned evidence |
| --- | --- | --- |
| **SC-C01** | Given an anonymous visitor and valid distinct values, when they sign up and then log in, the app confirms creation, requires the explicit login, and shows the new client's name and username with empty reservations. | R-01, BR-C01/02, account service. HTTP integration and rendered signup/sign-in. |
| **SC-C02** | Given a signed-in client, when they save a valid new display name and reopen the app against the same database, the new name remains and their username and user ID are stable. Repeating the save has the same result. | R-01 local extension and I-05, BR-C03/05/06, profile service. HTTP integration and persistence check. |
| **SC-C03** | Given an existing username or two simultaneous signups for one new username, attempts after the first creation fail with a safe duplicate result. The original account, password and profile are preserved. | R-01, BR-C02/05, account service. Duplicate and concurrent HTTP integration. |
| **SC-C04** | Given invalid fields, an injected role or identity field, or a missing/wrong CSRF token, when signup or a profile write is submitted, it is refused with no data changes. With CSRF and input both invalid, the CSRF refusal wins. A signed-in account attempting signup is refused. | R-01 / C-39, BR-C01–03, HTTP adapter and account/profile service. Negative integration tests. |
| **SC-C05** | Given an unauthenticated visitor, the seeded trainer, or a client trying to target a different client, when they request protected profile data or try to alter another account, they get no other user's data and neither account changes. | R-07 / I-05, BR-C03, route guards and profile service. Access checks on reads and writes. |
| **SC-C06** | Given a new signed-in client and an available future training, when the client reads membership and submits a valid booking request, membership is null and the existing membership refusal leaves the seat count and reservations unchanged. | R-02 / I-06, BR-C04, membership and booking services. HTTP regression using a registered client. |
| **SC-C07** | Given an injected persistence failure during creation or name update, when the operation runs, the client gets a safe failure and no partial account or changed profile remains. Given a committed signup with a lost response, explicit login works and only one account exists. | R-01, BR-C05, account service and storage. Rollback and uncertain response checks. |
| **SC-C08** | Given a disposable populated v0.1.1 database and seeded accounts, when the upgrade is applied and the app reopens, the original login, existing session, trainer schedule read, client booking/cancellation and history pass. Reapplying the upgrade preserves data. | R-01/02/07, BR-C06 and SC-P01–SC-P20. Upgrade integration and existing suites. |
| **SC-C09** | Given the site in a desktop and phone-width browser, when a user visits signup, handles an invalid field, signs in and updates the profile, the Slovak forms, messages and navigation remain usable with no horizontal overflow. | R-01, BR-C01–03, client portal. Manual walkthrough with recorded viewport and observed results. |

## Impact on v0.1.1

New use cases add account creation and own-profile access. The existing login, logout, session user-summary shape, client-only membership and reservations, and trainer schedule read are compatibility requirements. Keep booking and cancellation HTTP behavior, timing, membership precedence, ownership, cancellation history, replay handling and concurrent capacity exactly as approved. Existing browser booking reconciliation remains in use.

SC-P20 currently asserts the exact path set in the generated booking schema. Recommended for INC-01: preserve `/openapi.json` as the v0.1.1 booking schema and describe the new HTTP operations in their own proposed versioned contract. Combining the schemas is a separate documentation/interface decision. Verify all existing checks along with the INC-01 scenarios before reporting completion.

## Next task

After the user confirms the INC-01 scope and resolves DEC-C08, run **DESIGN_CONTRACT for INC-01 only**, using booking baseline v0.1.1. Write `prototype/spec/drafts/increment-01-client-account-http-v0.1.0.md` with status **Proposed**. Specify the registration and profile pages, account creation and profile read/update HTTP operations, and reuse of the existing session/login/logout operations. Include an OpenAPI 3.1 fragment for the new JSON operations, field schemas and limits, authorization and CSRF, validation and error order, successful navigation, retry and failure semantics, and compatibility with the exact v0.1.1 booking contract and schema. Map each new operation to its requirement, responsible service/component, data, BR-C rule and SC-C scenario. Return the specific proposed version for human approval. Implementation begins only after the user explicitly approves its scope and contract and authorizes that phase.
