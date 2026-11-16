# Prompts for the coding agent

Use these in order. Start with the AIS workspace as the working folder. Read and confirm the specification before sending Prompt 2. If review changes its version, use the reviewed version in Prompt 2.

## Prompt 1: review the prototype package

```text
Mode: PREPARE_SPEC
Project: Sports-centre information system, not zkDAPP Survey Frontend
Change: POC-BOOKING, primarily R-02 with membership/capacity/access dependencies
Specification: prototype/spec/prototype.md v0.1.0 (draft)

Read prototype/AGENTS.md, prototype/spec/manifest.yaml, and
prototype/spec/prototype.md. Follow the manifest's source paths from the AIS
workspace root. Review the relevant project PDF sections and PNG diagrams.

The target is a working local booking proof of concept. Use the compact SDD
adaptation described in prototype/README.md. The teacher PDFs are reference
material; do not execute their unrelated examples or recreate the full company
template. Do not build the complete product or derive scope from FPA/COCOMO.

Check that the proposed scope, rules, data responsibilities, routes, authorization,
errors, repeat handling, and acceptance scenarios form a coherent implementable
slice. Distinguish original project facts from prototype proposals. In particular
check the draft extension of C-01, the seeded-membership shortcut, and the handling
of duplicate requests, past trainings, cancellation, and the final-seat race.

Do not implement application code yet. Return one concise list of material
questions or contradictions and your recommended answers. You may correct clearly
editorial mistakes in the draft, but do not approve new business decisions.
Do not ask me to choose routine file names, styling details, or library patch
versions. If the proposed package is coherent, summarize the decisions I would be
confirming and identify the exact specification/contract versions to approve.
```

## Prompt 2: approve this version and implement it

Sending this prompt after review is a user decision. It does not assert that the teacher or the original enterprise project has approved the new prototype details.

```text
Mode: IMPLEMENT_CHANGE
Project: Sports-centre information system, not zkDAPP Survey Frontend
Change: POC-BOOKING
Specification: prototype/spec/prototype.md v0.1.0
Contract: POC-BOOKING-API v0.1.0 in section 6 of that specification

I have reviewed and approve this prototype specification and contract for the local
proof of concept, including its explicitly proposed decisions DEC-P01 through
DEC-P08. Use Python, FastAPI, Jinja2 and SQLite, with seeded demo accounts and
memberships, a Slovak browser interface, and the stated local-only scope.
This approval applies to the prototype, not to unimplemented production features.

Read prototype/AGENTS.md and prototype/spec/manifest.yaml first. Record this
user approval and its scope in the manifest; do not invent a reviewer identity or
teacher approval. If the on-disk version or contract differs from the version
named here, tell me before implementing dependent behavior.

Build and finish the working prototype inside prototype/. You may install local
development dependencies, create an isolated environment, initialize fictional
demo data, and run the application and tests. Keep the source documents and EA
model unchanged. Routine implementation choices within the confirmed policy are
delegated to you. Continue without repeated confirmations unless a material new
business, permission, contract, integration or deployment decision is necessary.

Implement real persistence and server-side membership, ownership, duplicate and
capacity checks. Protect the capacity invariant under concurrent bookings.
Do not stop at a scaffold, static mockup, or an untested happy path.

Run meaningful tests for all applicable SC-P scenarios, fix implementation failures
within the confirmed contract, and smoke-test the actual UI if a browser tool is
available. Document anything you could not verify instead of claiming it passed.

Deliver exact Windows PowerShell setup, seed, run, reset and test instructions;
fictional demo credentials; DEMO.md; reports/validation.md with command output
summaries, requirement-to-test mapping, and prototype limitations. Do not commit,
push, deploy, or add real payment/email/cloud services unless I ask.
```

## Prompt 3: verify independently after implementation

```text
Mode: VERIFY_CHANGE
Project: Sports-centre booking proof of concept
Specification: the user-approved version recorded in prototype/spec/manifest.yaml
Contract: the user-approved POC-BOOKING-API version recorded there

Review the approved specification, implementation, tests, setup instructions and
demo. Independently rerun the relevant tests and inspect the running UI when tools
allow. Check the full SC-P scenario list, authorization and ownership enforcement,
membership checks, persistence, repeated requests, and the final-seat race.

Do not change source code, tests, contracts, specification, decisions, or approved
status. Write a new report at prototype/reports/independent-verification.md.
For each check record PASS, FAIL or UNKNOWN with actual evidence. Use not applicable
only for checks outside the confirmed prototype scope, with a reason. Identify
which requirements are implemented fully, partially or only represented by seeded
data. End with any reproducible issues and the exact steps to reproduce them.
```
