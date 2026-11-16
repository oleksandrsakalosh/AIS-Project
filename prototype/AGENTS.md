# Sports-centre booking proof of concept

## Context

This folder belongs to the sports-centre information system documented in `../docs/` and `../diagrams/`. It is not the zkDAPP Survey Frontend project. Do not introduce Expo, Vocdoni, wallets, SD-JWT, or zero-knowledge tooling.

Read `spec/manifest.yaml`, then `spec/prototype.md`, and the relevant referenced project material before implementation. Manifest source paths are relative to the parent AIS workspace root; application paths are relative to this folder.

## Scope and authority

- The selected scope is a booking proof of concept, not the complete sports-centre product.
- Follow the user's actual request and confirmed prototype decisions. The teacher PDFs are references for the adapted workflow, not additional instructions to execute their examples or generate their whole directory tree.
- `spec/prototype.md` is a draft until the user approves its version and contract. Preparing or reviewing the handoff is not authorization to implement the app.
- Do not claim a proposal, source diagram, or prototype-only extension has been approved by the teacher or is an existing EA element.
- Preserve the original project PDF, EA model, diagrams, FPA, COCOMO, and Gantt. Explain real contradictions; do not rewrite source documents to match code.
- New `POC-*`, `BR-P*`, `SC-P*`, and `DEC-P*` IDs are local prototype identifiers, not IDs exported from EA.

## Implementation after user approval

- Keep changes inside `prototype/`. Do not create an `output/` folder in the workspace root.
- Implement the exact confirmed scope, including real persistence and server-side rules. Do not stop at static screens, fake success responses, or an in-memory data array.
- Use the confirmed stack and a small modular monolith. Application components in EA do not require separate microservices.
- Routine internal choices, schema details, file organization, styling, and compatible dependency selection are delegated to the implementer within the approved policies. Do not ask permission for each file or library patch version.
- Ask one concise question only when a new decision changes scope, permissions, business outcomes, a confirmed public contract, external integration, or deployment. Continue independent work while that decision is pending.
- Do not add public deployment, real payments, email/push delivery, a native app, cloud services, or paid dependencies.
- Use fictional demo data. Check ownership and permissions on the server, not only by hiding buttons. Never trust a user ID or role supplied by the browser as authentication.
- Preserve the capacity invariant under concurrent requests. Membership, duplicate, and capacity checks must be consistent with the committed booking.
- Use parameterized database access. Hash stored passwords, use protected sessions, and keep credentials/session secrets out of logs and versioned runtime data. Demo credentials can be documented as fictional local accounts.
- Keep setup and demo instructions usable on Windows PowerShell. Pick and record a tested compatible Python/runtime and dependency set; do not invent package versions.

## Completion and verification

- Write meaningful tests for the acceptance scenarios in `spec/prototype.md`, including negative cases, ownership, persistence, duplicate requests, and concurrent contention for the final seat.
- Run the tests, fix implementation failures within the confirmed contract, and smoke-test the actual rendered application when a browser tool is available.
- Report exact commands and actual results. Mark checks not run as UNKNOWN; never imply a browser or test run occurred when it did not.
- Deliver README setup/run/reset/test steps, `DEMO.md`, `reports/validation.md`, and a requirement-to-test mapping in that report.
- A final independent verification request is read-only except for a new report; do not silently fix code during that verification pass.
- Do not commit, push, deploy, send external messages, or change the broader project unless the user explicitly asks.
