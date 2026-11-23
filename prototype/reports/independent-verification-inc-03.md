# INC-03 independent verification

2026-11-23 · VERIFY_CHANGE · Sports-centre booking prototype

**Result — FAIL on SC-CAT03 and SC-CAT08.** An unchanged legacy label can return a name conflict. Reloading the browser after a lost create response discards the recovery key, and retrying the same trainer creation can produce a duplicate. An invalid UTF-8 request returns a different status and error shape from the approved contract. All 94 automated tests passed. The staff landing page now fits at 320 CSS pixels for administrators and receptionists.

## Scope and sources

The manifest records local approval of INC-03-CATALOG-ADMIN-HTTP v0.1.0 and DEC-C02, DEC-C10, DEC-C11 and DEC-C12. Verification used the approved INC-03 contract, INC-02 account lifecycle and the POC-BOOKING-API v0.1.1 baseline. This report is the only repository change from this verification. Tests and browser sessions used disposable databases with fictional data. [Manifest](../spec/manifest.yaml) · [INC-03 contract](../spec/drafts/increment-03-catalog-administration-http-v0.1.0.md) · [INC-02 contract](../spec/drafts/increment-02-account-administration-http-v0.1.0.md) · [Booking baseline](../spec/prototype.md#6-approved-api-contract)

The archived project specification assigns R-05 to administrators and traces it to R-54, G-43 and AC-05-1. It also assigns R-07 account administration to administrators. The archived GAP analysis places CP-02 in Gap A, after CP-01 account administration and before CP-03 scheduling. The native EA baseline remains unverified. [Source archive, project specification pp. 15–19 and GAP analysis pp. 5–6](../../docs/docs.zip)

The local R-05 slice provides persistent catalog lists, writes and trainer links, subject to the failures below. R-07 includes the linked-trainer account lifecycle guard. The approved local booking and cancellation behavior passed regression checks. Training times, capacities and membership examples remain seeded. INC-04 owns scheduling writes and active-only selection for new assignments.

## Commands and evidence

Run the commands from `prototype/`, except `git archive` and `git diff --check`, which ran from the repository root.

| Check | Observed evidence |
| --- | --- |
| `& ./.venv/Scripts/python.exe --version` and `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **PASS.** Python 3.13.7. 94 passed in 24.24 s. |
| `& ./.venv/Scripts/python.exe -m venv <temp>`, then the temporary interpreter with `-m pip install --disable-pip-version-check -r requirements.txt`, `-m pip check` and `-m pytest -q -p no:cacheprovider` | **PASS.** The pinned dependencies installed from cached wheels and passed `pip check`. 94 passed in 20.45 s. Both runs emitted one Starlette TestClient deprecation warning about `httpx`. |
| `node --version`, `node --test tests/mutations.test.mjs`, `node --check app/static/app.js`, `node --check app/static/catalog.mjs`, `& ./.venv/Scripts/python.exe -m pip check` and `& ./.venv/Scripts/python.exe -m compileall -q app tests` | **PASS.** Node v24.13.1, three JavaScript tests passed, and the syntax, dependency and compilation checks succeeded. |
| `git archive --format=tar --output=<archive> <commit> prototype/app`, `tar -xf <archive> -C <temp>`, archived `python -m app.seed --db <db>`, then current `python -m app.migrate --db <db>` twice | **PASS.** `5a321c7` (0.1.1), `dfb351a` (0.2.0) and `a8c2389` (0.3.0) each upgraded to 0.4.0. Every rerun reported current. Compared the original columns and rows in all eight data tables. Pre-upgrade Client and Trainer sessions worked after reopening each database. SQLite integrity and foreign-key checks passed. |
| `python -m app.seed --db <db>`, `app.bootstrap_admin.bootstrap` with a fictional administrator, then `python -m uvicorn app.main:app --host 127.0.0.1 --port 0 --no-access-log` with `POC_DB_PATH` set to that database | **PASS** for startup and `GET /health`. Playwright 1.65.2 drove Chrome 157.0.8103.80 at 1440 × 844 and 320 × 844 for catalog flows and at 390 × 844 for the Client compatibility check. Browser results for recovery appear below. |
| `GET /openapi.json` against `spec/openapi.generated.json` | **PASS.** The live API reports 0.3.0 and includes the four catalog paths. The six baseline paths outside the INC-02 login and session extension matched exactly. |
| `git diff --check` | **PASS.** Git reported line-ending conversion notices for existing edits. |

## Requirement, rule and scenario trace

The test names below refer to the repository suites. Controlled API and browser probes supplemented those tests using separate databases and sessions. [Catalog tests](../tests/test_catalog.py) · [Account administration tests](../tests/test_admin.py) · [Client account tests](../tests/test_accounts.py) · [Booking tests](../tests/test_acceptance.py)

| Scenario and trace | Result and evidence |
| --- | --- |
| SC-CAT01 · R-05 / CP-02 and R-07 / I-05 → BR-CAT01 → catalog HTML and list GET | **PASS.** `test_SC_CAT01_08_catalog_access_and_error_order` checked admin-only access, role redirects, exact fields, ordering and `no-store`. A separate empty-room fixture returned `200 {"items":[]}`. Chrome confirmed administrator navigation and Client and reception redirects. |
| SC-CAT02 · R-05 / AC-05-1 → BR-CAT02/05 → create POST | **PASS** for the API. `test_SC_CAT02_03_04_create_rename_deactivate_and_replay` covered each kind, NFC normalization, scoped original receipts through rename and deactivation, conflicting reuse, trainer homonyms and inactive room/activity name reservation. Chrome created all three kinds at both widths. Browser recovery is recorded under SC-CAT08. |
| SC-CAT03 · R-05 / AC-05-1 and R-02 → BR-CAT02/03/05 → name PUT | **FAIL** for an unchanged legacy label. Regular renames, inactive renames, stale versions, missing IDs and ordinary collision refusals passed the catalog lifecycle tests. An untouched migrated room name with decomposed Unicode and surrounding whitespace returned `409 catalog_name_taken`. A subsequent real rename to an unused name succeeded. |
| SC-CAT04 · R-05 / AC-05-1 → BR-CAT03/05 → status PUT | **PASS.** The catalog suite covered future references and a queued write crossing the start boundary, stale/current versions and reactivation refusal. A controlled fixture confirmed that a class with only a cancelled reservation blocked deactivation of all three kinds before start, and that all three deactivated at the exact start while the projected training remained readable. |
| SC-CAT05 · R-05 and R-07 / I-05 → BR-CAT04/05 → trainer account PUT | **PASS.** `test_SC_CAT05_06_link_lifecycle_and_account_guard` covered eligible first links, conflicts, future-assignment refusal, replacement, retained inactive links and clearing. Chrome linked at both widths, displayed the linked username and showed the existing-assignment explanation. |
| SC-CAT06 · R-07 / R-04 / R-05 → BR-CAT04/05 and BR-A04 → account status and role PUT | **PASS.** The suite and controlled probes verified refusal before start, preserved sessions and accepted each operation independently at the exact start. Each successful operation revoked the trainer session and retained the same catalog link and version. Restoring the account allowed fresh Trainer sign-in. INC-02 unlinked-account checks passed. |
| SC-CAT07 · R-05 and R-07 / I-05 → BR-CAT02/04/05 → catalog and account writes | **PASS.** `test_SC_CAT07*` covered same-key creates, name contention, stale write versions, a shared trainer account claim, both commit orders for linking against disable or role change, and revocation before the catalog write authorization check. |
| SC-CAT08 · R-05 / AC-05-1 and R-07 / I-05 → BR-CAT01/05/06 → HTML forms and JSON errors | **FAIL** for browser reload recovery and the malformed UTF-8 request. Chrome passed normal Slovak workflows, form cancellation for rename, stale edit refresh, and recovery from a failed picker read. Within the open page, a lost create response and failed list refresh held controls until a successful manual refresh. The recovery button sent the original key and returned one persisted row. A lost committed rename response reloaded version 2 without a second PUT. Valid authorization/CSRF precedence, ordinary malformed JSON, rollback with sanitized 500, and SQLite lock exhaustion with sanitized 503 passed. |
| SC-CAT09 · R-02 / C-60 / I-01 / I-04 / I-06 → BR-CAT03/07 and booking baseline → schedule, history and reservations | **PASS.** An API comparison found the renamed label was the only projection difference in the Client schedule, own history and staff aggregates. Tests also covered inactive historical references, ownership, membership denial, repeat requests and final-seat contention. In Chrome, Boris saw the new label, kept the seeded reservation ID, and cancelled that reservation successfully. |
| SC-CAT10 · R-04 / CP-03 → BR-CAT04/05/07 → catalog references and scheduling | **PASS** for the INC-03 boundary. Verified that historical reads resolve inactive IDs and catalog/account guards enforce future references. **OUTSIDE INC-03** for scheduling permissions, selectors, stale scheduling forms and scheduling races. The approved contract assigns those operations to INC-04. |
| SC-CAT11 · R-05 / CP-02 and R-02 → BR-CAT07 → migration, restart and reset | **PASS.** The archived CLI upgrades preserved existing data and sessions. `test_SC_CAT11_upgrade_seed_and_restart` checked restart, durable links and receipts, repeated initialization and reset. Account migration regressions covered rollback. Independent probes confirmed that migration refused a missing file, an unrelated database and an unsupported schema version without changing their observed contents. |

**INC-02 follow-up, SC-A10 — PASS.** At 320 CSS pixels, both staff sessions measured 320 px for the viewport and document and 226 px for the heading width and scroll width. The catalog also fit at 320 px with long labels. The earlier staff heading overflow did not reproduce. [Prior verification](independent-verification-inc-02.md#reproduction-for-sc-a10)

**UNKNOWN.** Physical-device behavior, formal accessibility conformance and elapsed time for one continuous five-minute demo. Chrome used emulated viewports. The browser checks exercised the relevant catalog and booking portions of the handoff. [README](../README.md) · [Demo](../DEMO.md)

## Reproductions

### 1. Reload loses the trainer create recovery key

1. Start the app on a freshly seeded temporary database, sign in as administrator and open **Katalóg → Tréneri**.
2. Intercept `POST /api/admin/catalog/trainers` in Playwright. Forward the request using `route.fetch()`, verify the server returned `201`, then abort the response to the page using `route.abort()`.
3. Enter a new trainer label and submit. Wait for the app to refresh the list and show **Overiť vytvorenie**. Reload the browser page before clicking that button.
4. The button has reverted to **Pridať položku**. Enter the same label and submit. Compare the two captured bodies and the resulting catalog. They used different `request_id` values and the list had two records for that label.

BR-CAT06 requires retaining the original request ID for the unresolved intent. The page holds that recovery state in an in-memory map. The API still returned the original receipt when the open page reused the key. [Browser implementation](../app/static/catalog.mjs)

### 2. Resubmitting an unchanged legacy room name returns a conflict

1. Seed a disposable database using `a8c2389` (schema 0.3.0). Insert two legacy room names using the parameter values `"  Sa\u0301la  "` and `"Sála"`. The first contains a decomposed accent and surrounding spaces.
2. Upgrade the database with `python -m app.migrate --db <db>`, bootstrap an administrator, and read `GET /api/admin/catalog/rooms` to get the exact stored first name, its ID and version 1.
3. Send that exact first name unchanged with `expected_version: 1` to `PUT /api/admin/catalog/rooms/{entry_id}/name`, with the admin cookie and CSRF token.

Expected `200` with the unchanged stored row at version 1 under BR-CAT02. Observed `409 catalog_name_taken`, because the submitted value was normalized before comparison to the raw stored name. Both room IDs and labels survived migration. [Rename implementation](../app/catalog.py) · [Name validation](../app/models.py)

### 3. Invalid UTF-8 bypasses the catalog validation envelope

1. With an active administrator session and valid CSRF token, send a `POST /api/admin/catalog/rooms` with `Content-Type: application/json`.
2. Send the raw Python body below. It contains byte `0xFF` at the name position.

   ```python
   b'{"name":"\xff","request_id":"a855853d-8874-4d29-b28d-d5ee7ad31d3f"}'
   ```

Expected `422` with `{"error":{"code":"validation","message":"validation"}}` under §3. Observed `400 {"detail":"There was an error parsing the body"}`. The room list was unchanged. Truncated UTF-8 JSON and an escaped lone surrogate returned the expected catalog validation error. [HTTP error handlers](../app/main.py)
