# User approval: POC-BOOKING v0.1.1

Recorded on 2026-11-16 from the user's explicit message in this conversation. No personal reviewer name, teacher approval, EA baseline certification or production approval is inferred.

Approved specification: `prototype/spec/prototype.md` **POC-BOOKING v0.1.1**.
Approved contract: **POC-BOOKING-API v0.1.1**, section 6 of that specification.

The user accepted all seven recommendations from PREPARE_SPEC and explicitly instructed:

> I approve DEC-P01–DEC-P08 and these seven amendments for this local proof of concept. Record this message as my approval of the resulting v0.1.1 specification and POC-BOOKING-API v0.1.1. This is prototype approval, not teacher approval or approval of production features.

The approved amendments are:

1. Attribute original `401 unauthorized` and `409 capacity_full` to C-01; label additional contract behavior as prototype extensions.
2. Use seeded pre-existing memberships without payment activation; check validity when booking, not at the training date; effective state before valid_from is pending.
3. Permit trainers to read the schedule while denying client-only membership/reservation operations.
4. Accept the delayed POST replay limitation after cancellation; never automatically retry booking POSTs; reconcile uncertain results first.
5. Preserve cancellation history, allow cancellation of owned future bookings despite expired membership, return cancelled state on repeats even after start, and give rebookings new IDs which old cancellation requests cannot affect. Retain past records without inventing completion.
6. Preserve capacity under actual concurrent requests, including final-seat and same-client contention; use fresh server time after lock waits/retries before checks and mutation/commit; test concurrent cancellation and time boundaries.
7. Apply authentication, role/CSRF, then validation error precedence, including combined failure cases.

The same message authorized IMPLEMENT_CHANGE immediately after saving these corrections, local development dependencies and routine implementation choices, acceptance tests, fixes, browser verification where possible, setup documentation, demo credentials, DEMO.md and validation evidence. No further approval gate is required for this agreed scope.

Teacher PDFs are reference material for the compact adaptation. Their unrelated examples and full company-style workflow are not implementation instructions.
