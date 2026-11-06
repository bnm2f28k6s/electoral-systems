/** Run directly, or receive Python parity cases on stdin. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { simulateRequest, simulateMultiRequest, FAMILY_METHODS, MULTI_FAMILY_METHODS } from '../typescript/api.ts';
import * as api from '../typescript/api.ts';
import type { BallotFamily, MultiBallotFamily } from '../typescript/api.ts';
import { simulate, ElectionError } from '../typescript/electoral.ts';
import { simulate as simulateMulti, ElectionError as MultiElectionError } from '../typescript/multi_winner.ts';

let checks = 0;
for (const multi of [false, true]) {
  const catalog = multi ? MULTI_FAMILY_METHODS : FAMILY_METHODS;
  assert.ok(Object.isFrozen(catalog));
  for (const methods of Object.values(catalog)) {
    assert.ok(Object.isFrozen(methods));
    assert.throws(() => (methods as unknown as string[]).push('sortition'), TypeError);
  }
  const dispatch = (request: unknown, family?: string) => multi
    ? simulateMultiRequest(request, family as MultiBallotFamily)
    : simulateRequest(request, family as BallotFamily);
  const engine = multi ? simulateMulti : simulate;
  const ErrorType = multi ? MultiElectionError : ElectionError;
  for (const [family, methods] of Object.entries(catalog)) for (const method of methods) {
    const request = JSON.parse(readFileSync(new URL(`../examples/${multi ? 'multi/' : ''}requests/${method}.json`, import.meta.url), 'utf8'));
    if (family === 'marked') for (const ballot of request.ballots) {
      const ranking = ballot.ranking;
      ballot.choice = method === 'anti-plurality' ? ranking.at(-1) : ranking[0];
      delete ballot.ranking;
    }
    const original = JSON.stringify(request);
    const functionName = `simulate${multi ? 'Multi' : ''}${family[0].toUpperCase()}${family.slice(1)}` as keyof typeof api;
    const specialized = api[functionName] as (input: unknown) => unknown;
    assert.deepEqual(specialized(request), engine(request));
    assert.throws(() => specialized({...request, method: 'not-a-method', ballots: []}), ErrorType);
    assert.deepEqual(dispatch(request, family), engine(request));
    assert.deepEqual(dispatch(request), engine(request));
    assert.equal(JSON.stringify(request), original, 'API must not mutate input');
    for (const [wrong, compatible] of Object.entries(catalog)) if (!compatible.includes(method)) {
      assert.throws(() => dispatch(request, wrong), ErrorType);
      assert.throws(() => dispatch({...request, ballots: []}, wrong), /compatible/);
    }
    for (const invalid of [null, [], {...request, method: []}, {...request, options: null},
      {...request, options: {seed: -1}}, {...request, options: {unknown: 1}}, {...request, ballots: null}])
      assert.throws(() => dispatch(invalid, family), ErrorType);
    assert.throws(() => dispatch({...request, candidates: Array.from({length: 33}, (_, i) => String(i))}, family),
      (e: any) => e instanceof ErrorType && e.status === 413);
    if (family !== 'none') {
      assert.throws(() => dispatch({...request, ballots: [{...request.ballots[0], count: true}]}, family), ErrorType);
      assert.throws(() => dispatch({...request, ballots: [{...request.ballots[0], count: 1000000}, request.ballots[0]]}, family),
        (e: any) => e instanceof ErrorType && e.status === 413);
    }
    checks++;
  }
  const both = {method: multi ? 'single-non-transferable' : 'plurality', candidates: ['A', 'B'],
    ...(multi ? {seats: 1} : {}), ballots: [{choice: 'A'}, {ranking: ['B', 'A']}]};
  assert.deepEqual(dispatch(both), engine(both));
  assert.throws(() => dispatch(both, 'ranked'), ErrorType);
  assert.throws(() => dispatch(both, 'marked'), ErrorType);
  assert.throws(() => dispatch(both, '__proto__'), ErrorType);
}
if (!process.stdin.isTTY) {
  let text = '';
  process.stdin.setEncoding('utf8');
  for await (const chunk of process.stdin) text += chunk;
  text = text.trim();
  if (text) for (const row of JSON.parse(text)) {
    const result = row.multi ? simulateMultiRequest(row.request, row.family) : simulateRequest(row.request, row.family);
    // Python and JS serialize exact fractions to IEEE doubles independently.
    function equivalent(actual: any, expected: any): void {
      if (typeof expected === 'number') assert.ok(Math.abs(actual - expected) <= 1e-12, `${actual} != ${expected}`);
      else if (Array.isArray(expected)) {assert.equal(actual.length, expected.length); expected.forEach((x, i) => equivalent(actual[i], x));}
      else if (expected && typeof expected === 'object') {
        assert.deepEqual(Object.keys(actual).sort(), Object.keys(expected).sort());
        for (const key of Object.keys(expected)) equivalent(actual[key], expected[key]);
      } else assert.equal(actual, expected);
    }
    equivalent(result, row.expected);
    checks++;
  }
}
console.log(`PASS: ${checks} family fixture/parity cases plus wrong-family, mixed-format, mutation, validation, and resource checks`);
