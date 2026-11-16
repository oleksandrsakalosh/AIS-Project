import test from 'node:test';
import assert from 'node:assert/strict';
import {submitOnce} from '../app/static/mutations.mjs';

test('SC-P20: lost committed response reconciles without replaying the POST', async () => {
  let posts = 0, persisted = 0, visible = 0;
  const result = await submitOnce(async () => {
    posts++; persisted++;
    throw new Error('response lost after commit');
  }, async () => { visible = persisted; });
  assert.equal(posts, 1);
  assert.equal(visible, 1);
  assert.equal(result.ok, false);
  assert.equal(result.reconciled, true);
});

test('SC-P20: failed reconciliation reports an unsafe-to-resubmit state', async () => {
  let posts = 0;
  const result = await submitOnce(async () => { posts++; throw new Error('timeout'); }, async () => { throw new Error('unavailable'); });
  assert.equal(posts, 1);
  assert.equal(result.reconciled, false);
});

test('SC-P20: successful mutation still reloads server-authoritative state', async () => {
  const calls = [];
  const result = await submitOnce(async () => { calls.push('POST'); return {id_rezervacie:7}; }, async () => { calls.push('read'); });
  assert.deepEqual(calls, ['POST','read']);
  assert.equal(result.result.id_rezervacie, 7);
  assert.equal(result.reconciled, true);
});
