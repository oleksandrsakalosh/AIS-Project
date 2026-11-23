# INC-01 independent verification

2026-11-23 · VERIFY_CHANGE · Sports-centre booking prototype

**Result: FAIL on responsive acceptance (SC-C09).** SC-C01–SC-C08 passed, along with the POC-BOOKING v0.1.1 regression checks exercised below. A valid 32-character username causes horizontal scrolling on the profile page at 320 and 360 CSS pixels. Application code, tests, specifications, decisions, and approval records were left untouched. All runtime checks used disposable databases.

## Scope and authority

The manifest records the approved POC-BOOKING and POC-BOOKING-API v0.1.1 baseline and identifies INC-01 as implemented. DEC-C08 records user authorization for local web signup, manual login, and own display-name editing. The delivered HTTP interface is documented as v0.1.0. **UNKNOWN** whether that exact HTTP interface was separately approved before implementation. The manifest and decision record establish the authorized behavior, and the preparation draft calls for a separate contract review. [Manifest](../spec/manifest.yaml) · [DEC-C08 and delivered HTTP interface](../spec/inc-01-client-account.md) · [Preparation draft](../spec/drafts/increment-01-client-registration.md)

The project PDF (pp. 15–18) specifies web or mobile self-registration under R-01, role-based access under I-05, and active membership for booking under I-06. Its example puts membership in a waiting state after registration. DEC-C08 intentionally creates no membership row. INC-01 implements the web self-registration slice of R-01 and the local display-name extension. R-07 is partially represented by client/trainer access enforcement. Account administration is outside INC-01. R-02 retains the baseline’s booking and cancellation subset. Membership, activities, rooms, trainers, and the initial schedule use seeded data. [Original project PDF](../../docs/Informačný_systém_pre_správu_športového_centra.pdf) · [Booking specification](../spec/prototype.md)

## Commands and observed evidence

Commands were run from `prototype/` unless noted.

| Check | Result |
| --- | --- |
| `& ./.venv/Scripts/python.exe --version` and `& ./.venv/Scripts/python.exe -m pytest -q` | **PASS** · Python 3.13.7, 65 tests passed in 9.10 s. One Starlette TestClient warning concerning deprecated `httpx` use. |
| `node --version` and `node --test tests/mutations.test.mjs` | **PASS** · Node v24.13.1, all 3 tests passed. |
| `& ./.venv/Scripts/python.exe -m pip check` and `& ./.venv/Scripts/python.exe -m compileall -q app tests` | **PASS** · No broken requirements or compilation errors reported. The existing virtual environment was used. Fresh environment installation is **UNKNOWN**. |
| `git archive --format=tar --output=<temp-archive> HEAD prototype` from the repository root, extract to a temporary directory, run the archived `app.seed --db <temp-db>`, then run current `& ./.venv/Scripts/python.exe -m app.migrate --db <temp-db>` twice | **PASS** · HEAD was `b95ed06`. The archived code created the v0.1.1 database, two authenticated sessions, and an additional booking. The current migration reported an upgrade to 0.2.0, then reported that the database was current. See SC-C08 for row counts and post-upgrade checks. |
| `& ./.venv/Scripts/python.exe -m app.seed --db <temp-db>` twice, then `& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 0 --no-access-log` with `POC_DB_PATH` pointing to that file | **PASS** · First seed initialized, second seed preserved the database, and `/health` returned 200. A separate Playwright Core 1.65.1 harness drove Chrome 157.0.8103.80 against the running server. Results appear in SC-C07, SC-C09, and SC-P20. |
| `git diff --check` from the repository root | **PASS** · No whitespace errors reported. Git emitted line-ending warnings on existing edits. |

## INC-01 requirement and scenario trace

| Scenario | Requirement → rule → operation | Result and evidence |
| --- | --- | --- |
| SC-C01 | R-01 → BR-C01/02 → signup, session, login, profile, reservations | **PASS** · `test_SC_C01_SC_C06_registration_is_account_only` and rendered browser flow. Signup retained the anonymous session. Explicit login gave client access, displayed the saved name and username, and showed an empty reservation list. The test checked the stored password hash. |
| SC-C02 | R-01 local extension, I-05 → BR-C03/05/06 → own profile GET/PUT | **PASS** · `test_SC_C02_own_name_survives_reopen_and_repeat` checked stable username and ID, repeated save, and database reopen. Chrome confirmed trimmed display name after reload and a fresh login. |
| SC-C03 | R-01 → BR-C02/05 → signup and login | **PASS** · `test_SC_C03_duplicate_signup_preserves_identity_and_credentials` checked mixed-case legacy collision and concurrent same-name creation. A single signup succeeded and the saved identity and credentials were preserved. |
| SC-C04 | R-01, C-39 → BR-C01–03 → signup and profile PUT | **PASS** · `test_SC_C04_invalid_signup_does_not_echo_values` and `test_SC_C04_SC_C05_csrf_role_and_ownership_precedence` exercised invalid and extra fields, signed-in signup refusal, sanitized errors, and CSRF before input validation. |
| SC-C05 | R-07 access subset, C-39, I-05 → BR-C03 → own profile GET/PUT and page | **PASS** · `test_SC_C04_SC_C05_csrf_role_and_ownership_precedence` and `test_SC_C09_page_navigation_respects_role` exercised anonymous and trainer denials, role redirects, and client identity from the session despite browser-supplied identifiers. |
| SC-C06 | R-02, I-06 → BR-C04 → current membership and booking POST | **PASS** · `test_SC_C01_SC_C06_registration_is_account_only` verified null membership, `403 membership_inactive`, and unchanged availability and reservations. Chrome showed the Slovak no-membership state and disabled booking. |
| SC-C07 | R-01 → BR-C05 → signup and profile PUT | **PASS** · `test_SC_C07_write_failures_rollback_and_a_committed_signup_can_be_recovered` verified sanitized failures, rollback and single-account persistence. At 390 × 844, Chrome lost the response after the server returned 201. The browser offered manual login, which succeeded, and issued one signup POST. |
| SC-C08 | R-01/02/07 → BR-C06 → upgrade, session, profile, schedule and reservations | **PASS** · `test_SC_C08_upgrade_preserves_sessions_and_booking_history` and independent CLI run from a database seeded by the committed baseline. The two migration runs preserved 5 users, 2 sessions, 4 memberships, 5 trainings, 4 reservations, 2 trainers, 5 activities and 2 rooms. SQLite integrity and foreign-key checks passed. Saved and fresh logins worked, the trainer could read the schedule, and the client could read, cancel and rebook. The full booking OpenAPI object matched `spec/openapi.generated.json`. |
| SC-C09 | R-01 and R-07 access subset → BR-C01–03 → signup, login, schedule and own profile pages | **FAIL** · Standard Slovak forms, validation feedback, keyboard tab order, role navigation, and reload passed at 1280 × 900 and 390 × 844 with typical usernames. A valid 32-character username overflowed the profile layout at 320 and 360 CSS pixels. See reproduction below. |

## Booking baseline regression

| Scenario | Result and evidence from this run |
| --- | --- |
| SC-P01, SC-P02 | **PASS** · TestClient verified login and session rotation, schedule occupancy, and trainer read access. |
| SC-P03, SC-P04, SC-P05, SC-P06 | **PASS** · Booking persistence, full-capacity refusal, membership states and boundaries, and duplicate precedence passed. |
| SC-P07, SC-P08, SC-P09 | **PASS** · Cancellation and repeat semantics, history, fresh rebooking ID, and old-ID cancellation isolation passed. |
| SC-P10, SC-P11, SC-P12 | **PASS** · Own-history scoping, client identity mismatch, authentication and trainer role boundaries passed. |
| SC-P13, SC-P14, SC-P15 | **PASS** · Exact start-time boundary, final-seat races between independent requests, same-client contention, cancellation races, refreshed time after lock wait/retry, and database reopen passed. |
| SC-P16, SC-P17, SC-P18, SC-P19 | **PASS** · CSRF and validation order, cancellation after membership expiry, injected rollback and sanitized errors, repeat seed and explicit reset on disposable databases passed. |
| SC-P20 | **PASS** for tested UI and reconciliation behavior. At 1280 × 900 and 390 × 844, Chrome verified invalid login feedback, schedule, booking with a seat decrement, own-list cancellation and history, restored availability, past-training labels, and logout revoking access. At 390 × 844, an intentionally dropped committed booking response triggered an authoritative refresh without a second POST. With that refresh also blocked, the browser disabled booking until manual refresh succeeded. The three Node tests and the full OpenAPI comparison also passed. |

**UNKNOWN** · Physical-device browser behavior, formal accessibility compliance and timing of the five-minute demo. A clean dependency installation was outside the observed setup smoke test.

## Reproduction: profile overflows with a valid maximum-length username

1. Start the prototype with a freshly seeded disposable database and open it in Chrome. In responsive mode set the viewport to 320 × 844 or 360 × 844 CSS pixels.
2. From **Zaregistrujte sa**, register using a username of 32 lowercase `w` characters, a valid display name, and a fictional password of at least 12 characters.
3. Follow **Prejsť na prihlásenie**, sign in, and open **Môj profil**.
4. Inspect the header and try to reach **Odhlásiť sa**. The document scroll width is 379 px at both viewport widths. The logout button’s right edge is 374 px from the left at the initial scroll position, so horizontal scrolling is required to see it in full. The same account fits at 390 px.

Expected under SC-C09: a valid account can use the phone-width profile and navigation without horizontal overflow.
