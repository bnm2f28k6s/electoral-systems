import assert from 'node:assert/strict';
import {parseRequest, LIMITS} from '../web/simulator.mjs';
const make = (method = 'plurality', n = 3, count = 1) => ({method, candidates: Array.from({length: n}, (_, i) => String(i)), ballots: [{ranking: Array.from({length: n}, (_, i) => String(i)), count}]});
const parse = (input, scope = 'single') => parseRequest(JSON.stringify(input), scope);
assert.equal(parse(make()).method, 'plurality');
assert.throws(() => parseRequest('x', 'single'));
assert.throws(() => parseRequest(' '.repeat(LIMITS.bytes + 1), 'single'), /bytes/);
assert.throws(() => parse(make(), 'unknown'), /domain/);
assert.throws(() => parse(make('plurality', 13)), /candidates/);
assert.throws(() => parse(make('plurality', 3, 1001)), /voters/);
assert.throws(() => parse(make('plurality', 3, -1)), /count/);
for (const [method, cap] of [['dodgson', 3], ['kemeny-young', 6], ['maximal-lotteries', 5]]) {
  parse(make(method, cap));
  assert.throws(() => parse(make(method, cap + 1)), /safety limit/);
}
assert.throws(() => parse(make('dodgson', 3, 8)), /Dodgson/);
for (const [method, cap] of [['proportional-approval', 6], ['minimax-external-opposition', 6], ['cpo-stv', 4], ['schulze-stv', 4], ['quota-borda', 6]]) {
  parse(make(method, cap), 'multi');
  assert.throws(() => parse(make(method, cap + 1), 'multi'), /safety limit/);
}
const groups = make(); groups.ballots = Array(101).fill({count: 1});
assert.throws(() => parse(groups), /groups/);
console.log('Simulator browser safety guards: PASS');
