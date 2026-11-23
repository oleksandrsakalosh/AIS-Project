# INC-01 implementation validation

**2026-11-23 · IMPLEMENT_CHANGE.** [DEC-C08 and delivered interface](../spec/inc-01-client-account.md). Verification used local temporary databases with the existing Windows Python 3.13.7 environment and Node v24.13.1. This report records implementation evidence.

## Observed checks

| Command or check, from `prototype/` | Result |
| --- | --- |
| `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` with `PYTHONDONTWRITEBYTECODE=1` | **PASS**, 65 tests in 9.82 s, including the original 48 and 17 account/upgrade cases. One existing Starlette TestClient deprecation warning. |
| `& ./.venv/Scripts/python.exe -m pip check` | **PASS**, no broken requirements. |
| `& ./.venv/Scripts/python.exe -m compileall -q app tests` with cache redirected to system temp | **PASS**. |
| `node --check app/static/app.js` and `node --test tests/mutations.test.mjs` | **PASS**, 3 booking reconciliation tests. |
| Compare `app.openapi()` with parsed `spec/openapi.generated.json` | **PASS**, exact structural equality with v0.1.1. |
| `& ./.venv/Scripts/python.exe -m app.migrate --db $copy` twice on a disposable v0.1.1 copy | **PASS**, upgraded to 0.2.0 and then reported current. SQLite integrity and foreign keys passed. The comparison to a control copy verified all existing rows in users, sessions, memberships, trainings, reservations, trainers, activities and rooms. The original runtime file hash matched the preparation baseline. |
| Chrome 157.0.8103.80 headless through a temporary Playwright Core 1.65.1 script against Uvicorn on loopback | **PASS** at 1280 × 900 and 390 × 844. Seeded an isolated SQLite file with `python -m app.seed --db <temp-file>` and served it via `POC_DB_PATH` with `python -m uvicorn app.main:app --host 127.0.0.1 --port <ephemeral-port> --no-access-log`. |

The first ad hoc migration comparison assumed the current runtime had the same reservation count as a fresh seed. The control copy showed four existing reservations. All four were preserved in the upgraded copy.

## Scenario evidence

| Scenario | Rules and evidence |
| --- | --- |
| SC-C01 and SC-C06 | BR-C01/02/04. `test_SC_C01_SC_C06_registration_is_account_only` verifies manual login, Client role, account persistence, a salted hash, schedule and blank reservation list. The current membership read is null and booking refuses with `membership_inactive` without consuming a seat. |
| SC-C02 | BR-C03/05/06. `test_SC_C02_own_name_survives_reopen_and_repeat` verifies persistent edits, stable username and ID, reopen and repeat, and another client's unchanged name. |
| SC-C03 | BR-C02/05. `test_SC_C03_duplicate_signup_preserves_identity_and_credentials` covers mixed-case legacy collision and concurrent registration with one successful insert. |
| SC-C04 and SC-C05 | BR-C01–03. Parameterized validation and access tests cover malformed input, forged fields, missing authorization, role, CSRF precedence, and owner scoping. Invalid signup responses do not echo submitted values. |
| SC-C07 | BR-C05. `test_SC_C07_write_failures_rollback_and_a_committed_signup_can_be_recovered` injects storage failures and verifies rollback. At phone width the browser check dropped the signup response after an observed server 201 and verified manual sign-in and one signup request. |
| SC-C08 | BR-C06. `test_SC_C08_upgrade_preserves_sessions_and_booking_history` covers a saved session, booking/history and trainer permissions across upgrade and reopen. The existing SC-P01–SC-P20 regression suite remains green. |
| SC-C09 | BR-C01–03. The HTML role and navigation test verifies redirects. The rendered browser check exercised Slovak signup, an invalid username error, keyboard Tab order, manual login, membership-gated schedule, and a profile edit surviving reload at both viewport sizes. No horizontal overflow or uncaught page errors were observed on the tested forms. |

Physical-device testing and formal accessibility verification remain **UNKNOWN**. See the [pre-change baseline](baseline-2026-11-23.md) for the earlier booking check scope.

## SC-C09 corrective recheck

The [independent verification](independent-verification.md#reproduction-profile-overflows-with-a-valid-maximum-length-username) found that a valid username of 32 lowercase `w` characters overflowed the profile at 320 and 360 CSS pixels. The account header now fits within the available width, the full username can wrap in both the header and profile, and the logout button retains its width.

| CSS viewport width | Profile scroll width before → after | Logout button right edge before → after |
| --- | --- | --- |
| 320 px | 379 → 320 px | 374 → 300 px |
| 360 px | 379 → 360 px | 374 → 340 px |

**PASS** in Chrome 157.0.8103.80 using the local Playwright Core harness and a fresh disposable database. The harness registered and manually signed in the maximum-length account, checked the full username and the logout button, and checked for horizontal overflow on Profile, Schedule, and My Reservations at 320, 360, 390, 768, 900, 1024, and 1280 CSS pixels. At 320 px, clicking logout returned to login and the profile API returned 401. The standard account and booking flows also passed at 390 and 1280 px.

`& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` passed all 65 tests with the existing TestClient warning. `node --test tests/mutations.test.mjs` passed all 3 tests. `git diff --check` passed.
