/** Independent behavior checks; run with Node 22.18+. */
import assert from 'node:assert/strict';
import { METHODS, simulate, ElectionError } from '../typescript/electoral.ts';
import type { ElectionRequest, Method } from '../typescript/electoral.ts';

const candidates = ['A', 'B', 'C'];
const ranked = [
  {ranking: ['A', 'B', 'C'], count: 3},
  {ranking: ['B', 'C', 'A'], count: 2},
  {ranking: ['C', 'B', 'A'], count: 2},
];
const approvals = [{approvals: ['A', 'B'], count: 3}, {approvals: ['B', 'C'], count: 2}, {approvals: ['C'], count: 2}];
const scores = [
  {scores: {A: 5, B: 4, C: 0}, count: 3},
  {scores: {A: 0, B: 5, C: 4}, count: 2},
  {scores: {A: 0, B: 3, C: 5}, count: 2},
];
function request(method: Method): ElectionRequest {
  const ballots = method === 'sortition' ? [] : method === 'approval' ? approvals : ['score', 'star', 'majority-judgment'].includes(method) ? scores : method === 'quadratic' ? scores.map(b => ({credits: b.scores, count: b.count})) : ranked;
  return {method, candidates, ballots};
}
let checks = 0;
for (const method of METHODS) {
  const counted = simulate(request(method));
  const expected = ['plurality', 'random-ballot', 'sortition'].includes(method) ? ['A'] : ['B'];
  assert.deepEqual(counted.winners, expected, method);
  assert.equal(counted.method, method);
  assert.equal(counted.tie, false);
  assert.ok(counted.trace.length > 0);
  checks++;
}

// The non-Condorcet 2:2:1 cycle has an asymmetric maximal lottery, not uniform.
const cyclic = {method: 'maximal-lotteries', candidates, ballots: [
  {ranking: ['A', 'B', 'C'], count: 2},
  {ranking: ['B', 'C', 'A'], count: 2},
  {ranking: ['C', 'A', 'B'], count: 1},
]};
assert.deepEqual(simulate(cyclic).lottery, [{candidate: 'A', probability: .6}, {candidate: 'B', probability: .2}, {candidate: 'C', probability: .2}]);

// Condorcet cycle: no candidate wins without a cycle-resolution rule.
const cycle = [{ranking: ['A', 'B', 'C']}, {ranking: ['B', 'C', 'A']}, {ranking: ['C', 'A', 'B']}];
for (const method of ['instant-runoff', 'baldwin', 'nanson', 'coombs', 'copeland', 'minimax', 'schulze', 'kemeny-young', 'dodgson']) {
  const answer = simulate({method, candidates, ballots: cycle});
  assert.deepEqual(answer.winners, candidates, `unresolved symmetric cycle for ${method}`);
  assert.equal(answer.tie, true);
}
assert.deepEqual(simulate({method: 'ranked-pairs', candidates, ballots: cycle}).winners, ['A']);

// Tied internal last places favor the earlier candidate, while a final tie is retained.
const irv = simulate({method: 'instant-runoff', candidates, ballots: [
  {ranking: ['A', 'B', 'C'], count: 3},
  {ranking: ['B', 'C', 'A'], count: 2},
  {ranking: ['C', 'B', 'A'], count: 2},
]});
assert.deepEqual(irv.winners, ['B']);
assert.deepEqual(irv.trace[0].eliminated, ['C']);
assert.deepEqual(simulate({method: 'plurality', candidates: ['A', 'B'], ballots: [{choice: 'A'}, {choice: 'B'}]}).winners, ['A', 'B']);

// The lower median is used for even electorates; one median removal breaks this tie.
const mj = simulate({method: 'majority-judgment', candidates: ['A', 'B'], ballots: [
  {scores: {A: 5, B: 4}}, {scores: {A: 3, B: 4}}, {scores: {A: 3, B: 3}}, {scores: {A: 0, B: 0}},
]});
assert.deepEqual(mj.winners, ['B']);
assert.deepEqual(mj.trace[0].majorityGrades, {A: 3, B: 3});

// Large counts remain compressed: equal grade distributions need no removal loop.
const large = simulate({method: 'majority-judgment', candidates: ['A', 'B'], ballots: [{scores: {A: 4, B: 4}, count: 1000000}]});
assert.deepEqual(large.winners, ['A', 'B']);
assert.equal(large.trace.length, 2);

// Arbitrary identifiers are own data keys, including names with JS prototype meanings.
const unusual = ['__proto__', 'constructor', 'toString'];
for (const method of ['borda', 'schulze', 'ranked-pairs', 'maximal-lotteries']) {
  assert.deepEqual(simulate({method, candidates: unusual, ballots: [{ranking: unusual, count: 3}]}).winners, ['__proto__']);
}

// Input formats are not silently coerced into one another.
for (const invalid of [
  {...request('borda'), ballots: [{ranking: ['A', 'B']}]},
  {...request('borda'), ballots: [{ranking: ['A', 'A', 'C']}]},
  {...request('score'), ballots: [{scores: {A: 5, B: 2}}]},
  {...request('score'), ballots: [{scores: {A: 5.5, B: 2, C: 1}}]},
  {...request('score'), ballots: [{scores: {A: 6, B: 2, C: 1}}]},
  {...request('approval'), ballots: [{approvals: ['A', 'A']}]},
  {...request('plurality'), ballots: [{choice: 'A', ranking: candidates}]},
  {...request('plurality'), ballots: [{choice: 'A', count: true}]},
  {...request('plurality'), ballots: [{choice: 'A', count: null}]},
  {...request('plurality'), options: null},
  {...request('plurality'), candidates: [' ']},
  {...request('quadratic'), ballots: [{credits: {A: 10, B: 1, C: 0}}]},
  {...request('sortition'), ballots: [{choice: 'A'}]},
]) assert.throws(() => simulate(invalid), ElectionError);
assert.throws(() => simulate({...request('dodgson'), ballots: [{ranking: candidates, count: 9}]}), (e: unknown) => e instanceof ElectionError && e.status === 413);
assert.throws(() => simulate({...request('borda'), ballots: [{ranking: candidates, count: 1000000}, {ranking: candidates}]}), (e: unknown) => e instanceof ElectionError && e.status === 413);

// Signed voice votes are permitted, and unspent budget is permitted.
assert.deepEqual(simulate({method: 'quadratic', candidates: ['A', 'B'], ballots: [{credits: {A: -2, B: 0}}]}).winners, ['B']);
console.log(`PASS: ${checks} TypeScript methods plus cycle, lottery, tie, grade, resource, identifier, and validation checks`);
