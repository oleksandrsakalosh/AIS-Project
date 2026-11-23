import test from 'node:test';
import assert from 'node:assert/strict';
import {trainingTime} from '../app/static/training-times.mjs';

test('SC-S03: a session through the Bratislava fall clock change displays both offsets', () => {
  assert.equal(trainingTime({
    starts_at: '2027-10-31T00:30:00.000000Z',
    ends_at: '2027-10-31T01:30:00.000000Z'
  }), '02:30 UTC+02:00 — 02:30 UTC+01:00');
});

test('SC-S03: a session crossing local midnight includes the end date', () => {
  assert.match(trainingTime({
    starts_at: '2027-01-18T22:30:00Z',
    ends_at: '2027-01-18T23:30:00Z'
  }), /^23:30 — .*19\..* 00:30$/);
});
