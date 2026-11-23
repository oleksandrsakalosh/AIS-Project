# Implementation validation: POC-BOOKING v0.1.1

For subsequent increments, see [INC-01 validation](validation-inc-01.md), [INC-02 validation](validation-inc-02.md), [INC-03 validation](validation-inc-03.md) and [INC-04 validation](validation-inc-04.md).

Date: **2026-11-16** (Europe/Budapest). Mode: **IMPLEMENT_CHANGE**.

Approved specification: `spec/prototype.md` v0.1.1. Approved contract: **POC-BOOKING-API v0.1.1**, section 6. Human approval is recorded in `spec/approval-v0.1.1.md` and the manifest. This report records implementation checks by the implementer; it is **not** the separate read-only independent verification, teacher approval, production acceptance or certification of the EA model.

## Result

**PASS:** 48 Python acceptance/API/storage tests, 3 JavaScript mutation tests, dependency consistency, Python compilation and JavaScript syntax. A second clean virtual environment installed the exact requirements and passed all 48 Python tests. Actual rendered UI checks passed on desktop and at 390 × 844 CSS pixels, including a real browser offline/reconciliation check. Booking survived an actual server process restart.

The local application was left running at **http://127.0.0.1:8000**. The explicit demo reset was exercised after verification, restoring the five users, five trainings and three seeded reservations; Anna again has no reservations. Reload any previously open page after this reset because it invalidates sessions/CSRF contexts.

## Tested environment

| Component | Actual tested value |
| --- | --- |
| OS / shell | Windows, Windows PowerShell |
| Python | 3.13.7 |
| SQLite | 3.50.4, Python standard-library adapter, WAL |
| FastAPI | 0.163.1 |
| Starlette | 1.10.0 |
| Pydantic | 2.14.3 |
| Uvicorn | 0.54.0 |
| Jinja2 | 3.1.6 |
| httpx / pytest | 0.28.1 / 9.2.0 |
| Optional Node test runner | v24.13.1; no npm packages |
| Rendered UI | Native Comet browser window controlled through Computer Use |

All direct and transitive Python package versions are pinned in `requirements.txt` from the actually installed environment. Node is optional for the three JavaScript tests and is not an application runtime/build dependency.

## Commands and observed results

Commands below ran from `prototype/` unless stated otherwise. No deployment, commit or push was performed.

| Command / check | Observed result | Status |
| --- | --- | --- |
| `python -m venv .venv` | Isolated Python environment created. | PASS |
| `& .\.venv\Scripts\python.exe -m pip install fastapi uvicorn jinja2 httpx pytest` | Dependencies resolved and installed successfully; versions frozen into requirements.txt. | PASS |
| `& .\.venv\Scripts\python.exe -m pytest -q` (initial) | 48 passed, 1 warning in 7.14s. | PASS |
| `& .\.venv\Scripts\python.exe -m pytest -q` (final) | **48 passed, 1 warning in 6.77s**. | PASS |
| `node --test tests/mutations.test.mjs` (final) | **3 passed, 0 failed**, approximately 52.5ms total. | PASS |
| `& .\.venv\Scripts\python.exe -m pip check` | `No broken requirements found.` | PASS |
| `& .\.venv\Scripts\python.exe -m compileall -q app tests` | Exit 0, no syntax errors. | PASS |
| `node --check app/static/app.js` | Exit 0, no syntax errors. | PASS |
| `python -m venv tmp/clean-venv` | A second empty environment created. | PASS |
| `& .\tmp\clean-venv\Scripts\python.exe -m pip install -r requirements.txt` | All pinned packages installed successfully. | PASS |
| `& .\tmp\clean-venv\Scripts\python.exe -m pytest -q` | **48 passed, 1 warning in 6.84s**. | PASS |
| `& .\.venv\Scripts\python.exe -m app.seed` | Empty default database initialized; repeat invocation preserved existing data. | PASS |
| `& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log` | Server started on loopback; no automatic seed/reset. | PASS |
| HTTP `GET /login`, `GET /health` | 200 HTML and `200 {"status":"ok"}` respectively. | PASS |
| Stop server with Ctrl+C; restart the same command without reset | Reservation 4 for Anna remained confirmed and visible with availability 1/3. | PASS |
| Stop server; `& .\.venv\Scripts\python.exe -m app.seed --reset-demo`; repeat `-m app.seed` | Reset restored fixtures; repeat printed `Existing database preserved; initialization made no changes.` | PASS |
| Inspect the reset database through parameterized SQLite reads | 3 reservations total, 0 for Anna, saved schema 0.1.1. | PASS |
| Parse YAML with the available system Python/PyYAML; check versions, statuses and manifest paths | Specification and contract both 0.1.1/approved; all project, PNG and teacher reference paths available. | PASS |
| Generate `spec/openapi.generated.json` from `app.openapi()` | API metadata version 0.1.1; application routes and typed read models present. Approved textual section 6 remains normative. | PASS |
| Final Python artifact assertions | All 20 SC-P IDs mapped in this report; generated OpenAPI equals current `app.openapi()`; all required handover files exist. | PASS |
| `git diff --check -- .` | Exit 0 after removing an editorial trailing space in README. Git also emitted its configured LF-to-CRLF notices. | PASS |

The single pytest warning is a **StarletteDeprecationWarning** that its httpx-backed TestClient integration is deprecated in favor of httpx2. The installed supported adapter still ran every test successfully in both environments. No warning is suppressed and no pass is inferred from an unrun test.

An initial ad hoc fixture-inspection `python -c` command had a PowerShell quoting SyntaxError. It did not modify data; the corrected here-string inspection passed. This was a verification-command error, not an application or acceptance-test failure.

## Scenario-to-test mapping

Python names below are in `tests/test_acceptance.py`; shared fixtures are in `tests/conftest.py`. Tests use temporary SQLite files and controlled clocks, never the user's default demo database.

| Scenario | Requirement / rule | Actual automated evidence | Result |
| --- | --- | --- | --- |
| SC-P01 | R-07 subset; BR-P02 | `test_SC_P01_login_credentials_and_session_rotation`: wrong/unknown credentials, cookie rotation, old-session rejection, hashes and cookie flags. | PASS |
| SC-P02 | R-02; BR-P01/P03 | `test_SC_P02_schedule_projection_and_trainer_read_access`: exact occupancy/free counts, own ID only, trainer read access, restricted fields. | PASS |
| SC-P03 | R-02; I-01/I-06 | `test_SC_P03_booking_persists_and_membership_need_not_cover_training`: persisted creation and membership expiring before training. | PASS |
| SC-P04 | C-60; I-01 | `test_SC_P04_full_training_has_no_mutation`. | PASS |
| SC-P05 | I-06; BR-P04 | `test_SC_P05_inactive_membership` (absent/pending/expired/not-yet-valid) and `test_SC_P05_validity_boundaries` (before/exact valid_from and before/exact valid_until). | PASS |
| SC-P06 | BR-P05 | `test_SC_P06_duplicate_precedes_full_and_inactive_membership`, plus SC-P13 started-over-duplicate precedence. | PASS |
| SC-P07 | R-02; BR-P06 | `test_SC_P07_SC_P08_cancel_history_and_repeat_after_start`: retained cancelled row and one-seat release. | PASS |
| SC-P08 | BR-P06 | Same combined test: repeated cancellation before/after start does not release another seat. | PASS |
| SC-P09 | BR-P08 | `test_SC_P09_rebooking_delayed_post_and_old_delete`: new ID, accepted delayed replay, old DELETE cannot cancel the newer booking. | PASS |
| SC-P10 | C-39; I-05 | `test_SC_P10_ownership_scoping_and_missing_ids`: own list, ignored query override, other-client/missing IDs concealed with 404. | PASS |
| SC-P11 | BR-P02; C-01 extension | `test_SC_P11_browser_identity_and_role_are_not_authentication`: client mismatch and forged identity cookie. Extra role input is also rejected in SC-P16. | PASS |
| SC-P12 | C-39; I-05 | `test_SC_P12_authentication_precedes_invalid_input_and_csrf` and `test_SC_P12_trainer_role_precedes_csrf_and_validation`: combined-failure precedence across protected routes. | PASS |
| SC-P13 | BR-P07 | `test_SC_P13_training_start_boundary_precedes_duplicate`: exact/past start, create/first cancel, unchanged records. | PASS |
| SC-P14 | I-01; BR-P01/P09 | `test_SC_P14_final_seat_real_concurrent_requests` (3 separate fixtures), `test_SC_P14_same_client_and_simultaneous_cancellation`, `test_SC_P14_create_cancel_race_preserves_capacity`, `test_SC_P14_fresh_clock_after_lock_wait_and_retry` (6 combinations). | PASS |
| SC-P15 | R-02 persistence | `test_SC_P15_application_reopen_uses_same_persistent_database`, plus actual Uvicorn process restart and browser reload described below. | PASS |
| SC-P16 | DEC-P06; BR-P09 | `test_SC_P16_csrf_precedes_malformed_body_and_path`, `test_SC_P16_login_logout_csrf_expiry_and_repeated_logout`: cross-session CSRF, malformed JSON, invalid/boolean/string IDs, role injection, logout and expiry. | PASS |
| SC-P17 | BR-P03/P04 | `test_SC_P17_expired_owner_can_cancel_but_not_book`. | PASS |
| SC-P18 | BR-P09 | `test_SC_P18_storage_failure_rolls_back_insert_and_is_sanitized` uses an actual SQLite AFTER INSERT failure; `test_SC_P18_unavailable_storage_does_not_create_an_empty_database` verifies 503/no fallback. | PASS |
| SC-P19 | DEC-P08 | `test_SC_P19_initialization_preserves_data_and_explicit_reset_restores_fixtures`, `test_SC_P19_reset_refuses_an_unrelated_database`, plus actual CLI reset/repeat. | PASS |
| SC-P20 | UI / reconciliation | `test_SC_P20_html_auth_pages_and_contract_metadata`; 3 tests in `tests/mutations.test.mjs`; actual desktop/390px UI and offline checks below. | PASS for the specified observed UI behaviors; timed rehearsal remains UNKNOWN. |

### Concurrency evidence details

Final-seat and same-client tests synchronize independent HTTP TestClient requests with a barrier, use independent SQLite connections, and run both requests concurrently through separate ASGI request contexts. They are not serial loops or one browser's disabled buttons. Final-seat trials return exactly `[201,409]`, with `capacity_full` for the losing different client and one committed seat. Same-client contention returns `duplicate_reservation`; simultaneous DELETEs both succeed with one release.

Boundary tests hold an actual SQLite write lock using an independent connection. An observed connection signals the request's `BEGIN IMMEDIATE` attempt; retry variants wait for a second real attempt after SQLITE_BUSY. The controlled clock then crosses membership expiry or training start before releasing the lock. Creates/cancellation are rejected using fresh time, with no forbidden mutation. Tests cover both a wait within one acquisition attempt and an actual acquisition retry.

The AFTER INSERT failure test deliberately raises SQLite FAIL after the insert executes; the transaction rolls back that partial insert, returns a sanitized 500 and leaves no booking. Missing/unavailable storage returns 503 and never silently creates another database or in-memory success.

## Actual rendered UI checks

The browser access host reported unavailable and returned no browser surfaces. The existing native Comet window was usable through Computer Use, so verification continued there in a new local-demo tab. This was a native rendered-browser check, not an inferred pass from HTTP/template tests. Screenshots and accessibility states were inspected during the session; no screenshot files are asserted as saved artifacts.

| Check | Observed result | Status |
| --- | --- | --- |
| Desktop login and readable error | Wrong Anna password displayed the Slovak error; valid fictional credentials opened her schedule. | PASS |
| Desktop schedule and booking | Initially 2/3 free for Funkčný tréning; booking confirmation displayed and free count became 1/3. Full and past trainings showed disabled actions. | PASS |
| Actual process restart | Stopped original Uvicorn process, started a new process against the same file, refreshed browser: same booking and free count survived; the persisted session also remained usable. | PASS |
| Own list and cancellation | Anna's reservation 4 appeared; cancellation kept it as ZRUŠENÁ and released its seat. | PASS |
| Phone-width layout | DevTools responsive viewport explicitly set to 390 × 844 CSS pixels; schedule, reservation history, navigation, cards and controls remained within the viewport without visible horizontal overflow. | PASS |
| Phone-width rebooking | Booked Funkčný tréning again; new persisted ID 5 (old ID 4 remains cancelled), visible confirmation and count update. | PASS |
| Offline failure / reconciliation block | With the demo tab offline, submitted once for Joga; network log showed one failed POST followed by the three reconciliation reads. Readable warning and disabled booking actions remained after reads failed. | PASS |
| Recovery without replay | Returned the tab to no throttling; no automatic POST replay occurred. Explicit Obnoviť údaje reloaded current state and re-enabled eligible actions. | PASS |
| Lost response after a committed write | JavaScript automated test simulates commit followed by lost response and proves one POST plus reconciled persisted state. This exact transport fault was not injected into the live browser. | PASS automated; live transport variant UNKNOWN |
| Trainer access | Trainer notice opened; schedule showed counts/read-only labels, no own-reservations navigation, membership data or booking buttons. Server/API role denials are separately automated. | PASS |
| Logout | Both client and trainer logout returned to the login page; API tests independently verify revoked access. | PASS |
| Dana/Cyril browser walkthrough | Membership/cancellation policies passed automated tests; these accounts were not separately exercised through the live UI during this turn. | UNKNOWN manual; PASS automated |
| Strict five-minute timed rehearsal | Repeatable script delivered in DEMO.md; elapsed presentation duration was not measured. | UNKNOWN |

Browser console inspection showed the intentional offline request failures, browser-extension warnings and a Perplexity-injected font blocked by the application's self-only CSP. There was no observed uncaught application JavaScript error during the successful flow. No security policy was weakened to accommodate browser extensions. Browser save-password prompts were dismissed; saving credentials was not requested.

A browser network smoke observation showed one successful booking POST taking **11ms** locally, followed by read refreshes around 32–33ms. This is an informal local observation with the current browser/extensions, not a defined-load benchmark, formal two-second acceptance or SLA certification.

## Original requirement coverage and architecture

| Original item | Coverage in this POC |
| --- | --- |
| R-02 / US-02 / C-01 | **Partial original requirement**, with working persistent create/cancel, history, errors and approved repeat policies. Original AC-02-1 also requires R-06 notification delivery, which is excluded. |
| C-60 / I-01 / I-04 | Implemented for the booking slice; availability and capacity enforced server-side under contention. |
| C-39 / I-05 / R-07 access subset | Implemented ownership and role enforcement; **R-07 partial**, with no account/permission administration. |
| I-06 | Implemented membership eligibility check with the user-approved temporal interpretation. |
| R-03 | **Seed-only membership dependency**, with effective validity reads/checks; no acquisition, activation, renewal or payment. |
| I-02 | Preserved by fictional fixtures/read-only membership data; no membership creation flow claimed. |
| R-04 / R-05 | **Seed-only** schedule, capacity, trainers, activities and rooms. No staff CRUD or planning flow claimed. |
| R-01 / R-06 / R-08 | Excluded: no registration, delivered notifications or native mobile application. Responsive browser layout does not complete R-08. |
| I-03 / payment audit | Outside the approved slice: no payments or fabricated settled records. |

The original PDFs and supplied views were read as project context; no original project source, EA model, diagram, FPA/COCOMO or Gantt file was written. Supplied application views map portal → reservation service → membership/schedule → persisted reservation; component names do not imply microservices. Membership and schedule remain read-only application responsibilities, while the booking service owns reservation writes using a shared transaction. Schema and indexes are implementation details under the expressly approved compact adaptation.

The supplied export baseline label and human verification against the current EA model remain unrecorded, as already disclosed in the manifest. No EA IDs, teacher approval or certified model baseline have been invented. Pre-existing user modifications to the root `.gitignore` and prototype handoff/instructions were preserved; implementation writes stayed within `prototype/`.

## Source availability and teacher-reference follow-up

All source paths in the manifest were available during this implementation turn. The three teacher references missing in the earlier PREPARE_SPEC turn are now available and were read:

| Source (relative to AIS root) | Relevant sections reviewed |
| --- | --- |
| `course_resources/SDD_framework_pre_studentov_v4.pdf` | pp. 2–3, 8–9, 12–15, 18 |
| `course_resources/SDD_AI_RULES_v4.pdf` | pp. 1–7 |
| `course_resources/SDD_PROJECT_TEMPLATE_v4.pdf` | pp. 1–5, 12–16 |

Their useful principles are retained: one coherent feature; explicit human approval of a concrete contract; responsibility/ownership boundaries; negative/repeat/concurrency scenarios; implementation judged against specification; honest traceability and evidence. The template explicitly treats its file tree and technologies as examples; the framework permits physical storage details to remain implementation details. The user's instruction selects a compact adaptation, so full company roles, separate ADR/template trees, unrelated pharmacy/delivery examples and new approval gates were not introduced. No claim of strict v4 compliance or teacher approval is made.

Project source sections and all seven manifest PNGs were reviewed during PREPARE_SPEC. Their readable context remains applicable; nothing in the newly available teacher references changed the approved booking business behavior. Current manifest-path verification found **no unavailable source**.

## Limits and remaining unperformed checks

The accepted delayed-POST-replay limitation after cancellation remains; no generic idempotency-key platform is implemented. Sessions/cookies are for a loopback HTTP POC, not production hosting. Comprehensive audit, external integrations, production load/security certification, accessibility certification and native-device testing are outside this approved scope. There is no automatic completed-booking transition or membership/payment lifecycle.

The explicit UNKNOWN manual checks above are not reported as passed. A separate independent VERIFY_CHANGE pass has not been requested or performed; its eventual report must remain separate and read-only with respect to application/specification changes.
