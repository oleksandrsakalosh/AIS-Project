# Sports-centre booking prototype: handoff

This folder is a specification and handoff package. The application has not been implemented yet.

The user selected a booking demo: accounts, seeded memberships, schedule, booking/cancellation, capacity and access checks. The intended result is a working local proof of concept for the sports-centre project, not a production release.

## Recommended approach

Use a compact adaptation of the teacher's Specification-Driven Development (SDD) approach:

1. Review one short specification and its proposed API contract.
2. Confirm the prototype decisions once.
3. Implement, test, demonstrate, and record the evidence.

Keep the link from project requirement to business rule, API operation, acceptance scenario, and test. Reuse the existing EA diagrams. Combine the textual requirements, decisions, contract, and scenarios in one file instead of creating the entire company-style directory tree.

This is an adaptation, not a claim of complete compliance with the v4 templates. If the teacher requires the exact v4 deliverables or approval records, retain this content and map it to those files. No teacher approval of the adaptation has been obtained.

The framework itself recommends one small end-to-end feature (framework pp. 2-3); the project template says its folder tree does not require creating every file (pp. 1-3). Technology examples are not mandatory prescriptions (template pp. 12-14). We retain their useful principle: agree on behavior before asking an agent to implement it.

## What is ready

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Short working instructions for the coding agent in this folder. |
| `spec/manifest.yaml` | Index of the scope, specification, source documents, and relevant diagrams. |
| `spec/prototype.md` | Proposed implementation brief, rules, screens, data, API contract, scenarios, and completion criteria. |
| `CODEX_PROMPTS.md` | Copyable prompts for review, implementation after your confirmation, and independent verification. |

The detailed choices are proposals. Only the booking-demo scope has already been selected by the user. The package does not label newly proposed behavior or technology as an approved original project requirement.

## Decisions to review before implementation

The recommended defaults are already written into the specification. You can accept them together or edit them before giving the implementation prompt.

| Decision | Recommended default | Why |
| --- | --- | --- |
| Delivery | Local responsive browser application | One runnable demo covers desktop and phone-sized views. Native mobile work would enlarge the scope. |
| Stack | Python + FastAPI + Jinja2 + SQLite; small amount of JavaScript | Reuses your Python preference from estimation, with one application and no separate frontend build. That earlier estimate did not itself approve the implementation stack. |
| Accounts | Seeded demo accounts and real login/logout; no registration or account administration | Enough to demonstrate identity and access checks. |
| Memberships | Seeded active, expired, and pending examples | Avoids inventing how Gap A confirms cash payments or implementing the draft online-payment flow. |
| Booking rules | Active membership at booking time, no duplicate active booking, no booking/cancellation after a training starts | Exact proposed behavior is in the specification. These details need your confirmation. |
| Infrastructure | One local process and one local SQLite file | No cloud account, payment credentials, deployment pipeline, or container setup needed. |
| Demo language | Slovak interface and demo instructions; English identifiers are fine | Fits the project's existing documentation and classroom demonstration. |

Also provide any teacher-specific acceptance rubric, required presentation length, mandated technology, or required authentication method if one exists. Those inputs are not present in this workspace. No secrets, real member data, payment-provider account, or production hosting details are needed for the proposed demo.

## How to give this to Codex

1. Keep this `prototype/` folder inside the current AIS workspace, next to `docs/`, `diagrams/`, and `course_resources/`.
2. Start the coding task with the AIS workspace as its root so the agent can read those relative paths. Explicitly say that this task is the **sports-centre system**, not zkDAPP Survey Frontend. The earlier project instructions in this conversation describe a different project.
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

- Teacher: `course_resources/SDD_framework_pre_studentov_v4.pdf`, especially pp. 2-3, 8-9, 12-15, and 18.
- Teacher: `course_resources/SDD_AI_RULES_v4.pdf`, especially pp. 1-7, for separating drafts, decisions, and implementation evidence.
- Teacher: `course_resources/SDD_PROJECT_TEMPLATE_v4.pdf`, especially pp. 1-5 and 12-16.
- FastAPI templates: https://fastapi.tiangolo.com/advanced/templates/
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Python SQLite: https://docs.python.org/3/library/sqlite3.html
- Codex instructions: https://developers.openai.com/codex/guides/agents-md/
