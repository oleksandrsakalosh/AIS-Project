# INC-03 implementation validation

2026-11-23 · Local sports-centre course project · **INC-03-CATALOG-ADMIN-HTTP v0.1.0**

**PASS for the implemented catalog and trainer-link scope.** The administrator can add, rename and deactivate trainers, activities and rooms. An explicit trainer link activates the previously approved account assignment guard. Existing schedule and history projections resolve catalog entries by ID and show their current labels. [Contract and approval](../spec/drafts/increment-03-catalog-administration-http-v0.1.0.md) · [Manifest](../spec/manifest.yaml)

## Checks run

| Command or check from `prototype/` | Observed result |
| --- | --- |
| `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests` | **PASS.** Python 3.13.7. All 94 tests passed in 20.35 s. Starlette emitted the existing `httpx` TestClient deprecation warning. |
| `node --check app/static/app.js`, `node --check app/static/catalog.mjs` and `node --test tests/mutations.test.mjs` | **PASS.** Node v24.13.1. Both syntax checks and all three mutation tests passed. |
| `& ./.venv/Scripts/python.exe -m pip check` and `& ./.venv/Scripts/python.exe -m compileall -q app tests` | **PASS.** No broken requirements. Compilation completed. |
| Compare `app.openapi()` with `spec/openapi.generated.json` and check the live route set in `test_SC_P20_html_auth_pages_and_contract_metadata` | **PASS.** All six baseline path definitions outside the INC-02 login and session extension match. The live schema reports 0.3.0 and includes the four catalog paths. |
| `git archive <revision> prototype/app`, then archived `python -m app.seed --db <temp-db>` and current `python -m app.migrate --db <temp-db>` twice per database | **PASS.** Databases created by commits `5a321c7` (0.1.1), `dfb351a` (0.2.0) and `a8c2389` (0.3.0) each upgraded to SQLite schema 0.4.0 and reported current on rerun. Compared pre-existing columns and rows for all eight data tables. SQLite integrity and foreign-key checks passed. Existing trainer records were unlinked. |
| Playwright 1.65.2 against Uvicorn on loopback, installed Chrome 157.0.8103.80, separate disposable databases, 1440 × 900 and 320 × 844 viewports | **PASS.** Admin sign-in and catalog navigation, all three catalog types, 80-character rename, deactivation, trainer linking, and future assignment refusals passed at both widths. `/staff` and the catalog fit at 320 CSS pixels. In a separate client context, the renamed activity appeared in the schedule and existing history, the same reservation could be cancelled, and direct catalog navigation returned to the client schedule. |
| Browser fault injection at 320 CSS pixels | **PASS.** Dropped a committed create response and the first reconciliation read. Controls stayed blocked until a successful manual refresh. An explicit recovery action resent the exact request ID and produced one persisted row. Dropped a committed rename response. The UI reloaded the renamed row and its new version after one PUT. |

## Requirements and scenarios

| Scenario | Result and evidence |
| --- | --- |
| SC-CAT01 · R-05 / CP-02 and R-07 / I-05 | **PASS.** `test_SC_CAT01_08_catalog_access_and_error_order` covered protected reads and writes, role redirects, exact list fields, `no-store` and ordering. The browser exercised admin navigation and client refusal. |
| SC-CAT02 and SC-CAT03 · R-05 / AC-05-1 | **PASS.** `test_SC_CAT02_03_04_create_rename_deactivate_and_replay` covered all three kinds, normalization, archived-label uniqueness, trainer homonyms, accepted replays, mismatched request IDs, stale edits and rename refusals. |
| SC-CAT04 · R-05 / AC-05-1 | **PASS.** Catalog lifecycle tests verified deactivation and exact version behavior. `test_SC_CAT04_future_reference_includes_empty_and_cancelled_bookings` covered empty training, cancelled-only booking references and the exact training-start boundary across a queued write. |
| SC-CAT05 and SC-CAT06 · R-05, R-07 and approved INC-02 BR-A04 | **PASS.** `test_SC_CAT05_06_link_lifecycle_and_account_guard` covered initial linking, replacement, clearance, the inactive-link case, invalid targets, ownership conflicts and session effects. Account disable and a role change away from Trainer were refused while a linked future assignment existed. |
| SC-CAT07 · R-05, R-07 / I-05 | **PASS.** The concurrency tests covered same-key creates, name contention, same-version writes, one account claimed by two trainers and both commit orders for trainer link versus account disable/role change. A queued request whose administrator was revoked received `401`. |
| SC-CAT08 · R-05 / AC-05-1 and R-07 / I-05 | **PASS.** API tests exercised access, role, CSRF, validation and rollback order. A failed receipt insert rolled back the entry and did not disclose the storage detail. Browser checks exercised narrow and desktop layout, Slovak feedback and reconciliation after dropped responses. |
| SC-CAT09 · R-02 / C-01 / C-60 | **PASS.** Catalog integration, booking baseline and browser checks covered current labels, history with inactive references, exact reservation IDs, caller privacy, cancellation, membership, duplicate and final-seat behavior. |
| SC-CAT10 · R-04 / CP-03 scheduling boundary | Existing inactive-reference resolution and the catalog/account future guards passed. **INC-04 owns the pending scheduling acceptance cases**, including active-only selectors, trainer ownership on schedule writes and concurrent scheduling versus deactivation. |
| SC-CAT11 · R-05 / CP-02 and R-02 preservation | **PASS.** Verified archived CLI migrations, preservation across restart, rollback on failed migration, explicit demo reset and durable catalog changes, links and receipts. |

Test coverage is in [test_catalog.py](../tests/test_catalog.py), [test_acceptance.py](../tests/test_acceptance.py), [test_admin.py](../tests/test_admin.py) and [test_accounts.py](../tests/test_accounts.py). Physical-device behavior is **UNKNOWN**. The browser checks used Chrome viewport emulation.

## Follow-up to independent verification

Reproduced all three failures on disposable data before changing the implementation. The fixes implement the existing v0.1.0 contract. [Independent verification findings](independent-verification-inc-03.md#reproductions)

| Finding | Retest result |
| --- | --- |
| SC-CAT03 · Unchanged migrated name with a normalized collision | **PASS.** `test_SC_CAT03_unchanged_migrated_label_preserves_legacy_collision` replays the decomposed, padded label and its equivalent normalized spelling. Both return `200` with the original name, ID and version. A real conflicting rename still returns `409`. A rename to an unused label succeeds. |
| SC-CAT08 · Trainer creation after reload | **PASS.** Using Chrome 157.0.8103.80 and Playwright 1.65.2 at 320 × 844, dropped the first committed response and reloaded the page. Reload sent no POST. The explicit recovery action sent the original body and key, leaving one trainer row. A subsequent reload returned the form to normal. Simulated browser storage failure sent no create request, and logout cleared an unresolved intent. |
| SC-CAT08 · Invalid UTF-8 in catalog JSON | **PASS.** `test_SC_CAT08_invalid_utf8_uses_catalog_validation` covers POST and PUT. An authorized request with malformed UTF-8 returns the exact sanitized `422 validation` envelope and leaves the catalog unchanged. Authentication, role and CSRF refusals still take precedence. |

From `prototype/`, `& ./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` passed **97 tests** in 21.39 s with the existing Starlette TestClient deprecation warning. The two `node --check` commands above, `node --test tests/mutations.test.mjs`, Python compilation, `pip check`, and `git diff --check` passed. The original desktop and phone-width browser walkthroughs also passed on rerun.
