# INC-04 implementation validation

**2026-11-23 · IMPLEMENT_CHANGE · Local course project**

**PASS** for trainer scheduling under DEC-C03, DEC-C04, DEC-C13 and DEC-C14. The live staff editor and scheduling API use the existing booking transaction boundary. All 125 Python tests and 3 JavaScript tests passed. Chrome exercised the trainer editor, the client booking flow and recovery from lost responses at desktop and phone widths. [Approved contract and approval](../spec/drafts/increment-04-trainer-scheduling-http-v0.1.0.md#7-approval) · [Manifest](../spec/manifest.yaml)

## Commands and results

Commands ran from `prototype/` unless noted. Tests, migrations and browser checks used temporary SQLite databases and fictional data.

| Check | Result |
| --- | --- |
| `& ./.venv/Scripts/python.exe --version` and `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **PASS.** Python 3.13.7. 125 passed in 31.40 s, including 28 trainer scheduling cases. The existing Starlette TestClient warning about httpx still appears. |
| `node --test tests/mutations.test.mjs` and `node --check` for `app/static/app.js`, `app/static/trainer-schedule.mjs` and `app/static/training-times.mjs` | **PASS.** Node v24.13.1. Three existing mutation tests passed. All three scripts passed syntax checks. |
| `& ./.venv/Scripts/python.exe -m pip check` and `& ./.venv/Scripts/python.exe -m compileall -q app tests` | **PASS.** Dependency and Python compilation checks passed. No application dependency changed. |
| `git archive --format=zip --output=<file> <revision> prototype/app` from the repository root, then each archived `python -m app.seed --db <path>` and current `python -m app.migrate --db <path>` twice | **PASS.** Seeded databases from `5a321c7` (0.1.1), `dfb351a` (0.2.0), `a8c2389` (0.3.0) and `3a57ca4` (0.4.0) reached 0.5.0. Compared each original table's rows and columns. SQLite integrity and foreign-key checks passed. All four reruns reported the database was already current. |
| `& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port <temporary-port> --no-access-log`, with `POC_DB_PATH` set to a disposable database | **PASS.** Playwright 1.65.2 drove Chrome 157.0.8103.80 at 1440 × 900, 320 × 844 and 390 × 844 CSS pixels. Contexts included device clocks in America/Los_Angeles and Asia/Tokyo. After restarting Uvicorn, the same trainer session read the edited training and replayed the original create result from the stored receipt. |
| Compare `app.openapi()` with the schema emitted from archived INC-03 revision `3a57ca4` | **PASS.** The 15 existing paths and their schema definitions matched exactly. The two trainer paths add GET/POST and PUT. |
| `git diff --check` from the repository root | **PASS.** Git reported working-copy line-ending conversion notices. |

## Requirement and acceptance evidence

| Scenario | Check and observed outcome |
| --- | --- |
| SC-S01 · R-04 and R-07 | **PASS.** `test_SC_S01_link_access_scope_and_redirects` checked role and link access, scope, expiry and ownership. Chrome showed the setup message before linking and the trainer's editor after linking. |
| SC-S02 · R-04 publish and edit | **PASS.** `test_SC_S02_publish_edit_and_validation` and `test_SC_S02_queued_create_crosses_start` checked publication, stable ID, input validation, CSRF precedence, the schedule projection and the start boundary. Chrome discarded a draft and confirmed it had no saved entry. |
| SC-S03 · R-04 time and allocation | **PASS.** `test_SC_S03_allocation_and_legacy_overlap` checked adjacency, parallel allocations, trainer and room conflicts, an ongoing training and correction of a legacy overlap. Chrome rejected the Bratislava spring gap and showed two selectable fall offsets with the same UTC instants at both widths. |
| SC-S04 · R-04 and R-02, C-60 / I-01 | **PASS.** `test_SC_S04_history_lock_and_capacity` checked capacity at occupancy and refusal below occupancy. Confirmed and cancelled reservations both locked the training's details. Chrome exercised the lock and saved a capacity-only edit. |
| SC-S05 · R-02 / CP-05 integration | **PASS.** `test_SC_S05_booking_contends_with_scheduling` exercised both commit orders for final-seat booking versus capacity and first booking versus a room change. Results matched the stored occupancy and committed session details. `test_SC_S05_cancellation_does_not_unlock_details` verified cancellation can make a reduction valid and cannot release the history lock. |
| SC-S06 · R-04 replay, allocations and versions | **PASS.** `test_SC_S06_receipts_versions_and_relink` and `test_SC_S06_edit_races_create_for_same_allocation` checked simultaneous duplicate creates, receipt replay after edit/start, changed keys and bindings, same-version edits, and room/trainer contention. |
| SC-S07 · R-04/R-05/R-07 integration | **PASS.** `test_SC_S07_catalog_deactivation_race` and `test_SC_S07_first_assignment_guards` checked blocked deactivation and all four trainer lifecycle races in both commit orders. Existing INC-02/03 tests checked the exact start boundary. |
| SC-S08 · R-04/R-07 UI recovery and storage | **PASS.** `test_SC_S08_rollback_and_lock_exhaustion` checked sanitized errors and rollback. Chrome intercepted a committed POST and aborted its response and the follow-up refresh. A page reload recovered the same key and payload, and explicit replay returned one training. A lost committed PUT response refreshed the visible version without a second PUT. |
| SC-S09 · R-02 contract compatibility | **PASS.** In Chrome, a stale card triggered refresh and required a second click before sending any reservation POST. The confirmation showed the current committed details. Existing booking and catalog regression tests passed, including cancellation replay, membership and ownership checks, last-seat contention and live catalog labels in history. |
| SC-S10 · R-04 persistence and upgrade | **PASS.** `test_SC_S10_upgrade_preserves_links_receipts_on_restart_and_resets` and `test_SC_S10_migration_rolls_back_overcapacity` checked version backfill, receipt durability, reset, and rollback on invalid data. Archived CLI upgrades and a Uvicorn process restart supplied separate evidence. |

## Scope and evidence limits

INC-04 covers the local R-04/CP-03 scheduling slice and integrates it with existing CP-05 bookings, CP-02 catalog references and R-07 access. DEC-C14 keeps the booking request keyed by training ID. A concurrent edit can still commit after the client's preflight read, so a booking may use details that differ from the last displayed card. The existing booking response shape remains in effect, and the browser shows the committed details after reconciliation.

**UNKNOWN.** Physical-device layout and formal accessibility conformance. Browser checks used emulated widths. The existing workspace runtime database was left for the operator to migrate when ready. [Setup and migration](../README.md) · [Demo](../DEMO.md)

## Follow-up on independent verification

Both findings reproduced before the fix and passed on retest. The following evidence supplements the original implementation run above. [Independent verification findings](independent-verification-inc-04.md#reproductions)

| Finding | Retest and result |
| --- | --- |
| SC-S03 · Trainer display during the Bratislava fall clock change | **PASS.** Playwright 1.65.2 and Chrome 157.0.8103.80 against loopback Uvicorn showed `02:30 UTC+02:00 — 02:30 UTC+01:00` on both the trainer list and the shared schedule. Reopening the editor restored both offset selections. The check ran at 1440 × 900 in America/Los_Angeles and 320 × 844 in Asia/Tokyo. |
| SC-S10 · Legacy capacity above the editor's integer limit | **PASS.** On disposable databases seeded from archived revision `3a57ca4`, `& ./.venv/Scripts/python.exe -m app.migrate --db <path>` exited 1 for capacity `9007199254740992`. A full SQLite dump matched before and after refusal. Capacity `9007199254740991` survived the upgrade and its repeat, and the trainer schedule returned HTTP 200 with the exact capacity and free-place count. A regression test also verified refusal when an already-upgraded fixture contains an out-of-range capacity. |
| Regression suites | **PASS.** `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` ran 128 tests in 33.11 s with the existing TestClient warning. `node --test tests/mutations.test.mjs tests/training-times.test.mjs` passed 5 tests. `node --check` passed for `app/static/app.js`, `app/static/trainer-schedule.mjs` and `app/static/training-times.mjs`. |
