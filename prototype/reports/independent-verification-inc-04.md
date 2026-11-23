# Independent verification of INC-04

2026-11-23 · VERIFY_CHANGE · Sports-centre booking prototype

**FAIL for full acceptance.** Two cases reproduced independently. The trainer list collapses a one-hour session across the Bratislava fall clock change to a single displayed time. A schema 0.4.0 database with a capacity above the new editor limit upgrades successfully, then the trainer's entire editor list returns `500`. Both findings have reproduction steps below. [Approved INC-04 contract](../spec/drafts/increment-04-trainer-scheduling-http-v0.1.0.md) · [Approval manifest](../spec/manifest.yaml)

The local R-04 / CP-03 scheduling flow passed ordinary publication, ownership, editing and capacity checks. R-02 / CP-05 booking and cancellation, R-07 trainer access and the R-05 / CP-02 catalog guards passed the applicable verification checks. Membership eligibility still uses seeded data. Verification used fictional accounts and disposable databases, with application, tests, approvals and specifications read-only. [Booking baseline](../spec/prototype.md) · [Prepared increment scope](../spec/drafts/course-project-preparation.md#implementation-increments)

## Commands and evidence

PowerShell commands ran from `prototype/`, with Git commands run from the repository root.

| Check | Result |
| --- | --- |
| `& ./.venv/Scripts/python.exe --version` and `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **PASS.** Python 3.13.7. 125 passed in 30.16 s. Starlette emitted one TestClient deprecation warning about `httpx`. |
| `node --version`, `node --test tests/mutations.test.mjs`, and `node --check` for `app/static/app.js`, `app/static/trainer-schedule.mjs` and `app/static/training-times.mjs` | **PASS.** Node v24.13.1. All three mutation tests and syntax checks passed. |
| `& ./.venv/Scripts/python.exe -m pip check`, installed-version comparison against `requirements.txt`, and in-memory compilation of Python files under `app/` and `tests/` | **PASS.** All 25 pins matched. All 21 Python files compiled. |
| `git archive --format=zip --output=<archive> <revision> prototype/app`, archived `python -m app.seed --db <db>`, then current `python -m app.migrate --db <db>` twice and `python -m app.seed --db <db>` | **PASS** for standard fixtures from `5a321c7` (0.1.1), `dfb351a` (0.2.0), `a8c2389` (0.3.0) and `3a57ca4` (0.4.0). Original table columns and rows matched, training versions backfilled to 1, SQLite integrity and foreign-key checks passed, and reseeding preserved the database. Pre-upgrade Client and Trainer sessions from 0.4.0 worked after reopening. A controlled legacy overlap remained readable. Missing, foreign and unsupported databases exited with code 1 and were left intact. **FAIL** for the upper-bound capacity fixture below. |
| Compare `create_app(<db>).openapi()` with the schema from archived `3a57ca4` | **PASS.** All 15 existing paths and their schema definitions matched. |
| Playwright 1.65.2 with Chrome 157.0.8103.80 against a loopback Uvicorn server running `create_app(<db>)` | **PASS** for trainer setup, normal saves, lost-response recovery and Client confirmation and cancellation. Exercised the trainer UI at 1440 × 900 and 320 × 844 CSS pixels with device time zones of America/Los_Angeles and Asia/Tokyo, and the Client UI at 390 × 844 in Asia/Tokyo. **FAIL** for the trainer list's repeated-hour display below. |
| `git -c core.safecrlf=false diff --check` | **PASS.** No whitespace errors. |

## Requirement, rule and acceptance trace

The listed tests ran in the full suite. Independent browser and API probes supplemented the scenarios. [Trainer scheduling tests](../tests/test_trainer_schedule.py) · [Booking tests](../tests/test_acceptance.py) · [Catalog tests](../tests/test_catalog.py) · [Account administration tests](../tests/test_admin.py)

| Scenario and trace | Result and evidence |
| --- | --- |
| SC-S01 · R-04 and R-07 / I-05 → BR-S01 → editor page and GET | **PASS.** `test_SC_S01_link_access_scope_and_redirects` checked role redirects, trainer-only writes, scoped reads, expiry and indistinguishable responses for missing and other-trainer IDs. Chrome showed the setup message and shared-schedule link before linking, then opened the editor after linking. A second linked Trainer with no classes saw the empty state. |
| SC-S02 · R-04 → BR-S01/02/04 → POST and PUT | **PASS.** `test_SC_S02_publish_edit_and_validation` and `test_SC_S02_queued_create_crosses_start` covered stable ID, version, committed UTC instants, invalid fields and IDs, error precedence and the start boundary. Independent raw malformed UTF-8 requests returned the `422 validation` envelope and `Cache-Control: no-store` on both methods. Discarding a draft at both widths left the editor snapshot identical. |
| SC-S03 · R-04 / CP-03 → BR-S02 → editor time entry, list and allocation writes | **FAIL for the trainer list.** `test_SC_S03_allocation_and_legacy_overlap` passed adjacency, ongoing and conflicting allocations, and permitted edits to legacy overlaps. Chrome rejected the spring gap, required both fall offsets at both widths and restored the selected offsets when reopening the edit form. The list collapsed a valid one-hour session to one time, while the shared schedule showed both offsets. |
| SC-S04 · R-04 and R-02 / C-60 → BR-S03 → capacity PUT and reservation history | **PASS.** `test_SC_S04_history_lock_and_capacity` verified refusal below occupancy, acceptance at occupancy, cancellation releasing the seat and the permanent history lock. Chrome showed the locked room and enabled capacity control after booking. Cancellation left zero occupancy and a true history flag. |
| SC-S05 · R-02 / CP-05 → BR-S03/05 and DEC-C14 → PUT and reservation writes | **PASS.** `test_SC_S05_booking_contends_with_scheduling` and `test_SC_S05_cancellation_does_not_unlock_details` covered both orders for booking versus reduction and first booking versus detail edits, reduction after cancellation and persistent locking. In Chrome, an edit committed after the Client's preflight and before the booking POST. The booking succeeded under the existing wire contract, and the reconciliation message and saved history showed the new room. |
| SC-S06 · R-04 → BR-S02/04/05 → scoped receipts and versioned writes | **PASS.** `test_SC_S06_receipts_versions_and_relink` and `test_SC_S06_edit_races_create_for_same_allocation` verified one persisted ID for same-key requests, identical receipt replay through edit and start, conflict after relinking or changing payload, stale versions, no-op and conflicts for the same trainer or room. |
| SC-S07 · R-04 and R-05/R-07 dependencies → BR-S01/05 → scheduling, account and catalog writes | **PASS.** `test_SC_S07_catalog_deactivation_race` and `test_SC_S07_first_assignment_guards` exercised both commit orders and stale catalog selections. The account and catalog regression suites passed the future-reference and session lifecycle guards. |
| SC-S08 · R-04 → BR-S04/05 → browser recovery, rollback and storage errors | **PASS.** Chrome lost a committed `201`, reloaded and reused the exact key and payload on explicit recovery. One class persisted. A lost committed PUT and failed refresh blocked saves, then manual refresh verified version 2 without a second PUT. A separate lost PUT crossed start and reported that the outcome could not be verified. An unlinked Trainer could not replay a pending create until the original link was restored. `test_SC_S08_rollback_and_lock_exhaustion` verified sanitized errors, lock exhaustion and transaction rollback of training and receipt. |
| SC-S09 · R-02 / C-60 / I-01/I-04/I-06 → DEC-C14 and booking baseline → shared schedule, history and reservations | **PASS.** Chrome detected a room change at preflight, sent zero POSTs on that click, and sent one unchanged reservation request only after a fresh click. The owner cancelled and retained history. Regression tests covered membership, delayed POST and old cancellation replay, duplicate and final-seat behavior, aggregate reads, and historical catalog labels under DEC-C10. |
| SC-S10 · R-04 with R-02/R-05/R-07 persistence → BR-S06 → migrate, restart and initialize/reset | **FAIL for the legacy capacity case.** Standard archived upgrades, repeated migration, initialization, session persistence and intentional overlaps passed. `test_SC_S10_upgrade_preserves_links_receipts_on_restart_and_resets` and `test_SC_S10_migration_rolls_back_overcapacity` passed receipt persistence, explicit reset and failed migration rollback. The independent capacity probe upgraded a fixture beyond the new allowed range and then received `500` on the trainer GET. |

**UNKNOWN.** Physical-device behavior, formal accessibility conformance and timing for a single uninterrupted demo. The browser used emulated viewport sizes. [Setup](../README.md) · [Demo](../DEMO.md)

## Reproductions

### 1. Trainer list hides the end time across the Bratislava fall clock change

1. Seed a disposable database, bootstrap an administrator, then link `trener` to Marek Novák and sign in as `trener`.
2. In **Moje tréningy**, create a class with start and end both at Bratislava wall time `2027-10-31 02:30`. Pick `UTC+02:00` for start and `UTC+01:00` for end. Save before that date.
3. Read the class in the trainer list and in **Spoločný rozvrh**. The trainer list shows `31. 10. 2027, 2:30:00` with no end or offsets. The shared schedule shows `02:30 UTC+02:00 — 02:30 UTC+01:00`. Reopening the editor restores both selections, and the saved endpoints are `00:30Z` and `01:30Z`.

The trainer card uses `Intl.DateTimeFormat.formatRange` without offsets, so it collapses the two identical local times. The trainer list needs to represent both endpoints of the saved interval under the editor read and Bratislava time policy. [Trainer card](../app/static/trainer-schedule.mjs#L108) · [Contract §3](../spec/drafts/increment-04-trainer-scheduling-http-v0.1.0.md#3-browser-and-http-operations)

### 2. Upgrade accepts a legacy capacity that breaks the trainer editor read

1. Archive `3a57ca4` and run its `python -m app.seed --db <db>` against a disposable path. In that database, set `trainers.account_id = 5` for `trainers.id = 1`, and set `trainings.capacity = 9007199254740992` for `trainings.id = 1`. Keep training 1 in the future. The 0.4.0 schema accepts this positive integer.
2. Run the current `python -m app.migrate --db <db>`. It exits 0 and reports `Demo database upgraded.`
3. Run the current app against `<db>` and sign in as `trener`. `GET /trainings` returns `200`. `GET /api/trainer/schedule` returns `500 {"error":{"code":"internal_error","message":"internal error"}}`. In the browser this prevents the trainer from loading any of their future sessions in the editor.

The migration accepts the old capacity, while the editor response model rejects values above `9007199254740991`. A migration that cannot preserve valid editor reads must fail safely under BR-S06. The standard seeded capacities fall within the new range. [Migration check](../app/migrate.py#L57) · [Editor response model](../app/models.py#L180) · [Contract §4](../spec/drafts/increment-04-trainer-scheduling-http-v0.1.0.md#4-state-duplicates-and-concurrent-writes)
