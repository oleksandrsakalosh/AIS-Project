# INC-02 · Implementation validation

**2026-11-23 · IMPLEMENT_CHANGE · Local sports-centre course app**

**PASS** for the INC-02 account and access portion of R-07 / CP-01 and the applicable INC-01 and booking regressions. The user confirmed DEC-C01 and DEC-C09. The approved interface is INC-02-ACCOUNT-ADMIN-HTTP v0.1.0. [Contract and approval](../spec/drafts/increment-02-account-administration-http-v0.1.0.md#7-approval-and-decisions) · [Manifest](../spec/manifest.yaml)

## Evidence

Ran from `prototype/` on Windows with Python 3.13.7 and Node v24.13.1. Verification used disposable SQLite files.

| Check | Result |
| --- | --- |
| `& ./.venv/Scripts/python.exe -m pytest -q` | **PASS.** 80 tests in 15.57 seconds, including 15 INC-02 cases. Starlette emitted its existing TestClient deprecation warning about httpx. |
| `node --test tests/mutations.test.mjs` and `node --check app/static/app.js` | **PASS.** Three booking mutation tests and browser JavaScript syntax. |
| `& ./.venv/Scripts/python.exe -m pip check` and `& ./.venv/Scripts/python.exe -m compileall -q app tests` | **PASS.** No broken requirements or compilation errors. |
| `& ./.venv/Scripts/python.exe -m app.migrate --db <copy>` twice for each source schema | **PASS.** Disposable 0.1.1 and 0.2.0 databases used the Git-tracked DDL at `5a321c7` and `dfb351a`. The CLI upgraded both to 0.3.0 and reported each current on rerun. Row comparisons preserved user fields, sessions, bookings, memberships and catalog data. SQLite integrity and foreign-key checks passed. A new application instance accepted the saved Client cookie and returned the expected profile and booking. |
| Playwright 1.65.2 with Chrome 157.0.8103.80 at 1440 × 900 and 390 × 844 | **PASS.** Started the real app with `& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port <temporary-port> --no-access-log` and selected each disposable database using `POC_DB_PATH`. Exercised Slovak staff provisioning, account list, role change, sign-in redirects after revocation, disable/re-enable, self-demotion and read-only reception. Also booked and cancelled as a Client. Both sizes passed the overflow check and produced zero uncaught page errors. |
| Browser response loss during staff provisioning | **PASS** at both widths. Intercepted the response after an observed server 201 and verified exactly one POST. When the list refresh succeeded the UI showed the saved account and its current role/state. When the list refresh failed the form stayed blocked until a manual refresh succeeded. |

## SC-A10 responsive layout retest

**PASS after correction · 2026-11-23.** The staff heading now scales to fit narrow screens with wrapping available for larger text settings. Before the fix, both administrator and reception sessions reproduced a 324-pixel document at 320 CSS pixels and a 277-pixel heading inside a 266-pixel box at 360 CSS pixels. [Independent verification reproduction](independent-verification-inc-02.md#reproduction-for-sc-a10)

Retested the running app with Playwright 1.65.2 and Chrome 157.0.8103.80. Started from `prototype/` with `& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 0 --no-access-log` and `POC_DB_PATH` pointing to a disposable database. At 320 × 844, 360 × 844, 390 × 844 and 1440 × 900, the document and staff heading each fit their measured widths for both roles. The word **Zamestnanecký** fit on one line in every case. The administrator's account-management link and reception's schedule link loaded their destinations without browser errors.

The regression rerun passed all 80 Python tests and 3 JavaScript tests with `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` and `node --test tests/mutations.test.mjs`.

## Requirements and scenarios

Automated INC-02 tests are in `tests/test_admin.py`. Scenario prefixes below match test names. The original regression suite remains in `tests/test_acceptance.py`, `tests/test_accounts.py` and `tests/mutations.test.mjs`.

| Requirement / contract rules | Scenario | Result and evidence |
| --- | --- | --- |
| R-07 / CP-01 · BR-A01, BR-A02 | SC-A01 | **PASS.** `test_SC_A01_cli_bootstrap_validates_and_preserves_identity` invokes the CLI entry point with simulated terminal input. It verifies validation, unrelated or missing storage, duplicate username, first sign-in and repeat refusal. `test_SC_A01_concurrent_bootstrap` verifies a single winner. |
| R-07 / C-39 / I-05 · BR-A01, BR-A05, BR-A06 | SC-A02, SC-A10 | **PASS.** `test_SC_A02_A10_visibility_and_error_order` covers row projection, role and HTML redirects, aggregate-only schedule, authorization/CSRF/input order, strict path and version values, and login validation without echoed credentials. The browser walkthrough checked the corresponding desktop and phone paths. |
| R-07 and R-01 compatibility · BR-A01, BR-A06, BR-A07 | SC-A03 | **PASS.** `test_SC_A03_provisioning_and_shared_username_uniqueness` exercises all staff roles, legacy-case conflicts, disabled usernames, field/role refusals and a concurrent signup/provisioning collision. |
| R-07 and R-02 compatibility · BR-A02, BR-A03, BR-A05, BR-A06 | SC-A04–SC-A06 | **PASS.** `test_SC_A04_A05_disable_preserves_client_history_and_rejects_future_seats` exercises multiple revoked sessions, generic invalid credentials, re-enable against the same ID, history, expired membership and exact start boundary. `test_SC_A06_last_admin_and_simultaneous_reductions` verifies last-admin protection and concurrent self-changes. |
| R-07, R-02, C-60 · BR-A03, BR-A05, BR-A06 | SC-A07 | **PASS.** `test_SC_A07_revoked_requests_waiting_at_the_write_boundary` gates already admitted booking, cancellation and profile writes until revocation commits. `test_SC_A07_booking_and_cancellation_commit_before_disable` checks the opposite ordering. |
| R-07 / I-05 · BR-A01, BR-A05, BR-A06 | SC-A08 | **PASS.** `test_SC_A08_role_changes_and_revocation` verifies staff role changes, revoked CSRF, demotion, disabled status preservation and fixed Client role. `test_SC_A08_login_racing_disable_checks_current_state` pauses login after loading credentials and verifies disable wins. |
| R-07 · BR-A05–BR-A07 | SC-A09 | **PASS.** `test_SC_A09_stale_versions_noop_and_atomic_failures` checks stale edits, no-ops, missing IDs and rollback of creation and revocation. The browser check verified recovery for both successful and failed reconciliation reads. |
| R-07 / CP-01 with R-02 compatibility · BR-A08 | SC-A11 | **PASS.** `test_SC_A11_migration_and_reset`, `test_SC_A11_failed_upgrade_rolls_back`, existing SC-C08 and the CLI upgrade and integrity checks cover migration, repeat, rollback, restart, retained IDs and reset/bootstrap. |
| R-01, R-02, R-07 / C-39 / C-60 / I-05 / I-06 | SC-A12 | **PASS.** Existing INC-01 and booking tests cover signup, owned profile, access and membership, ownership, duplicate and final-seat contention, expiry, cancellation and delayed replay. The live OpenAPI regression checks the original booking paths plus the admin routes and four session roles. |
| R-07 with future R-04/R-05 integration · BR-A04 | SC-A13 | **INC-03 boundary.** The approved linked-trainer guard depends on the explicit link introduced in INC-03. The unlinked case passed in SC-A08. |

The live combined OpenAPI identifies version 0.2.0. The local schema identifies version 0.3.0. The historical generated OpenAPI snapshot remains the v0.1.1 booking reference. [Original reference](../spec/openapi.generated.json)
