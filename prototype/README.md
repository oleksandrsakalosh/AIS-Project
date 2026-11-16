# Sports-centre booking prototype

Working local proof of concept for **POC-BOOKING specification v0.1.1** and **POC-BOOKING-API v0.1.1**. The user approved DEC-P01–DEC-P08 and seven review amendments on 2026-11-16; see [approval evidence](spec/approval-v0.1.1.md). This is prototype approval, not teacher approval or production certification.

## Spustenie vo Windows PowerShell

Tested with **Python 3.13.7** on Windows and the exact resolved package versions in `requirements.txt`. Python 3.13 is recommended for reproducing this tested environment. No Node build, database server, cloud account or API key is required. Use a browser with JavaScript enabled.

From the AIS workspace root:

```powershell
Set-Location prototype
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m app.seed
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open **http://127.0.0.1:8000**. Keep this PowerShell window open; stop the server with **Ctrl+C**. Calling the virtual environment's Python directly avoids PowerShell activation/execution-policy changes. If Python is unavailable, install Python 3.13 with pip first. If port 8000 is already used, pass `--port 8001` and open that port instead.

### Ukážkové účty

All passwords are **`Demo123!`**. These are fictional local accounts only.

| Username | Access / membership |
| --- | --- |
| `anna` | Client; active membership; initially no reservations. |
| `boris` | Client; active membership; owns the seeded bookings in trainings 1 and 3. |
| `cyril` | Client; expired membership; can cancel his earlier booking in training 5. |
| `dana` | Client; pending membership; cannot book. |
| `trener` | Trainer; schedule read access and staff notice; no client operations. |

### Dáta, reštart a reset

The SQLite database is `prototype/runtime/booking.sqlite3`, with WAL sidecar files while running. Runtime files, sessions and `.venv` are ignored by `prototype/.gitignore`; do not commit or share them. Database initialization is explicit: the server never seeds or resets automatically. Repeating `python -m app.seed` preserves existing data and the original saved training dates. Future dates are relative to the original seed timestamp, so reset old demo data before a later presentation.

Stop the server first. This command explicitly replaces only the recognized fictional demo data and invalidates its sessions:

```powershell
& .\.venv\Scripts\python.exe -m app.seed --reset-demo
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Reload the browser and sign in again after reset. `--db <path>` is available for a separate seed database; set `$env:POC_DB_PATH` to the same absolute path before starting the server. Reset refuses an unrelated database. Tests always use their own temporary databases.

### Testy

Run from `prototype/`:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m compileall -q app tests
```

The optional JavaScript mutation tests use Node's built-in test runner (no npm packages or frontend build). Node is **not** needed to run the application. The tested Node version and results are recorded in `reports/validation.md`.

```powershell
node --test tests/mutations.test.mjs
```

See [DEMO.md](DEMO.md) for the Slovak five-minute walkthrough and [validation evidence](reports/validation.md) for exact results and scenario mapping. The generated API schema is available locally at `/openapi.json` and `/docs`; [the approved textual contract](spec/prototype.md#6-approved-api-contract) remains authoritative. `spec/openapi.generated.json` is a generated implementation artifact, not a separately approved source of business rules.

### Implementation notes and limits

- FastAPI HTTP adapters call small authentication, membership, schedule and booking services over SQLite. There are no network calls between application modules.
- Passwords use salted scrypt hashes. Sessions use random opaque cookies, with only cookie hashes stored in SQLite. Cookies are HttpOnly and SameSite=Strict; all POST/DELETE calls require `X-CSRF-Token` obtained from `/session`. Login rotates the session. Sessions expire after 24 hours and are revoked on logout/reset. GET session also establishes an anonymous CSRF context.
- A write transaction acquires SQLite's `BEGIN IMMEDIATE` lock with a bounded five-second busy/retry window. Membership, training time, duplicate and occupancy checks share that transaction. Time is refreshed after waits/retries and immediately before the write; a partial unique index additionally protects confirmed duplicates.
- Booking POSTs are never automatically retried. An uncertain result reloads authoritative reservations and availability; failed reconciliation disables further booking until a successful refresh. After cancellation, a delayed old POST may create a new booking: this accepted limitation is not a generic idempotency system.
- Only confirmed bookings consume seats. Cancellation keeps history; rebooking uses a new ID, and old DELETE requests cannot cancel it. Past records do not automatically transition to completed.
- Memberships and schedule are fixtures, not administration or activation flows. Payments, notification delivery, registration, native mobile, deployment, comprehensive audit tooling and production security are excluded. Loopback HTTP cookies are intentionally not a production TLS configuration. No formal SLA, load, accessibility or external security certification is claimed.

## Original compact handoff context

The user selected a booking demo: accounts, seeded memberships, schedule, booking/cancellation, capacity and access checks. The intended result is a working local proof of concept for the sports-centre project, not a production release.

## Recommended approach

Use a compact adaptation of the teacher's Specification-Driven Development (SDD) approach:

1. Review one short specification and its proposed API contract.
2. Confirm the prototype decisions once.
3. Implement, test, demonstrate, and record the evidence.

Keep the link from project requirement to business rule, API operation, acceptance scenario, and test. Reuse the existing EA diagrams. Combine the textual requirements, decisions, contract, and scenarios in one file instead of creating the entire company-style directory tree.

This is an adaptation, not a claim of complete compliance with the v4 templates. If the teacher requires the exact v4 deliverables or approval records, retain this content and map it to those files. No teacher approval of the adaptation has been obtained.

The framework itself recommends one small end-to-end feature (framework pp. 2-3); the project template says its folder tree does not require creating every file (pp. 1-3). Technology examples are not mandatory prescriptions (template pp. 12-14). We retain their useful principle: agree on behavior before asking an agent to implement it.

## Package contents

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Short working instructions for the coding agent in this folder. |
| `spec/manifest.yaml` | Index of the scope, specification, source documents, and relevant diagrams. |
| `spec/prototype.md` | Approved v0.1.1 brief, rules, screens, data, API contract, scenarios, and completion criteria. |
| `CODEX_PROMPTS.md` | Copyable prompts for review, implementation after your confirmation, and independent verification. |

The user has now approved the detailed prototype choices. The package does not label prototype behavior or technology as an approved original project requirement.

## Confirmed prototype decisions

The defaults below were confirmed by the user with the v0.1.1 amendments. Further material changes require a new decision; routine implementation choices remain delegated.

| Decision | Recommended default | Why |
| --- | --- | --- |
| Delivery | Local responsive browser application | One runnable demo covers desktop and phone-sized views. Native mobile work would enlarge the scope. |
| Stack | Python + FastAPI + Jinja2 + SQLite; small amount of JavaScript | Reuses your Python preference from estimation, with one application and no separate frontend build. That earlier estimate did not itself approve the implementation stack. |
| Accounts | Seeded demo accounts and real login/logout; no registration or account administration | Enough to demonstrate identity and access checks. |
| Memberships | Seeded active, expired, and pending examples | Avoids inventing how Gap A confirms cash payments or implementing the draft online-payment flow. |
| Booking rules | Active membership at booking time, no duplicate confirmed booking, no new booking/first cancellation after training start | Approved behavior and repeat handling are in specification v0.1.1. |
| Infrastructure | One local process and one local SQLite file | No cloud account, payment credentials, deployment pipeline, or container setup needed. |
| Demo language | Slovak interface and demo instructions; English identifiers are fine | Fits the project's existing documentation and classroom demonstration. |

No teacher-specific acceptance rubric, required presentation length, mandated technology or authentication method has been supplied. This does not block the user-approved POC. No real member data, payment-provider account or production hosting details are needed.

## How to give this to Codex

The initial review and approval steps below have been completed for v0.1.1. The copyable prompts remain useful for subsequent review and independent verification; do not treat them as missing approval for the implementation already authorized here.

1. Keep this `prototype/` folder inside the current AIS workspace, next to `docs/`, `diagrams/`, and `course_resources/`.
2. Start the coding task with the AIS workspace as its root so the agent can read those relative paths.
3. Give the agent **Prompt 1** from `CODEX_PROMPTS.md`. It reviews the package and proposes any necessary corrections; it does not start coding.
4. Read the resulting questions and confirm the specification, especially the table above. If it changes, update the version in the manifest and in the implementation prompt.
5. Give **Prompt 2**. Sending it is your explicit approval of the stated prototype specification and contract, and your instruction to build it. It authorizes routine implementation decisions within that scope without repeated permission requests.
6. Use **Prompt 3** for a separate read-only verification when the prototype is ready.

The explicit read order in the prompts matters. Codex also uses `AGENTS.md` instructions for work in the folder where they apply; this file is intentionally inside `prototype/` so it does not replace instructions for unrelated work in the parent workspace.

If you move the prototype into a new repository, copy the referenced project PDF and the relevant PNG diagrams as well, then update the manifest paths. Giving an agent an absolute path to a file on another computer does not make that file available to it. The `.qea` model and full HTML report are optional context; readable PNG exports and the source PDF are enough for this slice.

## What the coding agent should read

The manifest identifies exact files. The important project content is:

- Project PDF: scope on p. 2, application responsibilities on pp. 5 and 11-14, requirements on pp. 15-16, invariants on p. 17, contracts and quality on p. 18, decisions on pp. 18-19.
- EA PNGs: Application Cooperation, Application Structure, Application Usage, Information Structure, Layered, Service Realization, and Technology Usage.
- GAP PDF pp. 5-6: how booking, membership, and later payments are separated.

FPA, COCOMO, and Gantt are planning material. They are not instructions to implement all 161 UFP, to generate a target number of code lines, to follow a predicted staffing level, or to create every production feature. A planning assumption is not an approved API contract.

The teacher's three PDFs are methodological reference material. This package deliberately adapts their workflow. Do not copy the unrelated delivery/pharmacy examples, sample IDs, company roles, or sample `approved` fields as project facts.

## Expected final handover from the coding agent

- A working application in this folder, with persistent local demo data.
- Exact Windows PowerShell setup, seed, run, reset, and test instructions.
- Seed account credentials using fictional users only.
- Automated tests mapped to the acceptance scenarios, including the last-seat race.
- A short `DEMO.md` with a repeatable five-minute walkthrough.
- `reports/validation.md` with actual commands/results and a distinction between passed checks and unperformed checks.
- A concise list of prototype shortcuts and limitations.

The prototype is complete when the specified scenarios work, not merely when a server starts or pages look finished.

## References for the proposed setup

All three teacher PDFs were available and read on 2026-11-16 after the initial review. Their relevant sections support selecting one coherent feature, explicit approval and evidence. This user-approved compact adaptation does not claim full v4 compliance or teacher approval. No referenced source was unavailable during the implementation turn.

- Teacher: `course_resources/SDD_framework_pre_studentov_v4.pdf`, especially pp. 2-3, 8-9, 12-15, and 18.
- Teacher: `course_resources/SDD_AI_RULES_v4.pdf`, especially pp. 1-7, for separating drafts, decisions, and implementation evidence.
- Teacher: `course_resources/SDD_PROJECT_TEMPLATE_v4.pdf`, especially pp. 1-5 and 12-16.
- FastAPI templates: https://fastapi.tiangolo.com/advanced/templates/
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Python SQLite: https://docs.python.org/3/library/sqlite3.html
- Codex instructions: https://developers.openai.com/codex/guides/agents-md/
