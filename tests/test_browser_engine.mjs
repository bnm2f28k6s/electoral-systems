/** Run after scripts/build.py. Tests emitted JavaScript, not Node's TS stripping. */
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {simulateRequest, simulateMultiRequest} from '../site/_build/_assets/engine/api.js';
import {simulate as single} from '../typescript/electoral.ts';
import {simulate as multi} from '../typescript/multi_winner.ts';

function equivalent(actual, expected) {
  if (typeof expected === 'number') {
    assert.equal(typeof actual, 'number');
    assert.ok(Math.abs(actual - expected) <= 1e-10 * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
  } else if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual));
    assert.equal(actual.length, expected.length);
    expected.forEach((value, i) => equivalent(actual[i], value));
  } else if (expected !== null && typeof expected === 'object') {
    assert.deepEqual(Object.keys(actual).sort(), Object.keys(expected).sort());
    for (const key of Object.keys(expected)) equivalent(actual[key], expected[key]);
  } else assert.deepEqual(actual, expected);
}

const results = [];
for (const [domain, prefix, compiled, source] of [
  ['single', '', simulateRequest, single],
  ['multi', 'multi/', simulateMultiRequest, multi],
]) {
  const catalog = JSON.parse(await readFile(new URL(`../data/${domain === 'multi' ? 'multi_' : ''}methods.json`, import.meta.url)));
  for (const {id} of catalog) {
    const load = async kind => JSON.parse(await readFile(new URL(`../examples/${prefix}${kind}/${id}.json`, import.meta.url)));
    const request = await load('requests');
    const before = structuredClone(request);
    const result = compiled(request);
    assert.deepEqual(result, source(request), `${domain}/${id}: compilation changed behavior`);
    equivalent(result, await load('responses'));
    assert.deepEqual(request, before, `${domain}/${id}: input mutated`);
    results.push({domain, method: id});
  }
}
assert.equal(results.length, 44);
for (const simulate of [simulateRequest, simulateMultiRequest]) {
  assert.throws(() => simulate(null));
  assert.throws(() => simulate({method: 'unknown'}));
}
console.log(`PASS: ${results.length} compiled browser methods match canonical engines and executed fixtures; invalid input rejected`);
