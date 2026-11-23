# Candidate AGENTS.md for the sports-centre course application

**Proposed in PREPARE_SPEC.** Intended destination is `prototype/AGENTS.md` after user adoption. Read `spec/manifest.yaml` first, then the relevant approved specification, contract and source extracts. Manifest paths are relative to the AIS workspace root. Use the tracked resource archives when loose exports are absent.

## Scope and authority

- The approved local baseline is POC-BOOKING and POC-BOOKING-API v0.1.1. Preserve that historical specification, generated reference and approval record. Booking behavior follows v0.1.1 except where a later versioned, explicitly approved change says otherwise.
- Course-project increments may add the approved portions of web registration/profile, accounts/roles, catalogs, scheduling, membership, simulated payment and an in-app inbox. Treat `spec/drafts/` as review material. A proposal, example approval, or project-PDF status alone does not authorize local implementation or imply teacher approval.
- Keep work inside `prototype/`. Use Python, FastAPI, Jinja2, SQLite and a small browser layer, with logical module ownership inside one process. Deliver Slovak responsive browser pages. Use local loopback, fictional data and clearly labelled simulation. Public deployment, live payments, external messages, native mobile, and unsupported cloud or paid infrastructure are outside scope.
- Use the project/GAP sources and existing EA exports for traceable context. Record substantive gaps or contradictions, and use the correct requirement or diagram ID family. Keep the source PDFs, models, diagrams, FPA, COCOMO and planning files intact. Local identifiers designate project proposals. Generated API docs describe the implementation.

## Compact change workflow

- **PREPARE_SPEC** verifies paths and baseline evidence and drafts the selected increment's requirements, rules, owners, lifecycle and scenarios. Save drafts under `spec/drafts/` and evidence under `reports/`. Preserve approved specifications, code, tests and runtime data during preparation.
- **DESIGN_CONTRACT** proposes a versioned interface for the named increment. Map operations to requirements, ownership, data, rules and scenarios. Specify error order, retries, access and compatibility. Record material unresolved decisions that affect the contract. Let the user approve the exact version.
- **IMPLEMENT_CHANGE** starts with the user's authorization and recorded approval of the named specification and contract. Implement the complete local flow. Routine storage, file layout, styling and compatible dependency choices are delegated within scope. Bring material scope, permission, business outcome, public contract or integration changes back to the user.
- **VERIFY_CHANGE** records results separately from implementation and keeps the approved materials and code read-only. Mark unperformed or unverified checks UNKNOWN. Keep a requirement → rule → contract → scenario → test trail and record actual commands, results and relevant manual checks. Update the manifest with versioned approval and evidence when authorized.

## Implementation and verification defaults

- Reuse existing authentication, server-side role/ownership checks, safe cookies, CSRF, password hashing and parameterized SQLite access. Keep sensitive data out of logs and committed fixtures. Test access against direct HTTP requests. Respect existing booking rules, including fresh time after lock waits, capacity, duplicate handling, cancellation history and reconciliation without automatically replaying a booking POST.
- Preserve persistent identities and history across explicit SQLite upgrades. Exercise updates, migrations, seed/reset and concurrency on temporary databases or disposable copies. Keep demo reset explicit and preserve existing data on normal startup.
- Run the v0.1.1 regression checks as applicable and the approved scenarios for each increment, including important denial, retry, storage and contention cases. Verify the rendered Slovak flow at desktop and phone widths when possible. Keep the Windows PowerShell setup, run/reset, tests and demo handoff usable.
- Local work stays local unless the user explicitly authorizes a commit, push, deployment, external send or broader project change.
