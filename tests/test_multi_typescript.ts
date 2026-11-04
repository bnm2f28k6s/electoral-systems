/** Independent behavior checks: node tests/test_multi_typescript.ts */
import assert from 'node:assert/strict';
import {METHODS, simulate, ElectionError, asNumber} from '../typescript/multi_winner.ts';
import type {Method, Ballot, ElectionRequest} from '../typescript/multi_winner.ts';

// Both operands overflow Number individually, but their rational ratio is finite.
const huge = 10n ** 400n;
assert.equal(asNumber([huge + 1n, huge]), 1);
assert.equal(asNumber([3n * huge + 1n, 2n * huge]), 1.5);
assert.equal(asNumber([huge + 1n, 3n * huge]), 1 / 3);
assert.equal(asNumber([-huge - 1n, huge]), -1);
assert.equal(asNumber([1n, 2n ** 1074n]), Number.MIN_VALUE);
assert.equal(asNumber([3n, 2n ** 1075n]), 2 * Number.MIN_VALUE);
assert.equal(asNumber([1n, 10n ** 500n]), 0);
assert.equal(asNumber([1n, 2n ** 1075n]), 0);
assert.equal(asNumber([2n ** 53n + 1n, 2n ** 53n]), 1);
assert.equal(asNumber([2n ** 53n + 3n, 2n ** 53n]), 1 + 2 ** -51);

const candidates = ['A', 'B', 'C', 'D'];
const ranked = [
  {ranking: ['A', 'B', 'C', 'D'], count: 6},
  {ranking: ['C', 'D', 'A', 'B'], count: 3},
  {ranking: ['D', 'C', 'B', 'A'], count: 1},
];
const approved = [
  {approvals: ['A', 'B'], count: 6},
  {approvals: ['C', 'D'], count: 3},
  {approvals: ['D'], count: 1},
];
const scores = [
  {scores: {A: 5, B: 4, C: 0, D: 0}, count: 6},
  {scores: {A: 0, B: 0, C: 5, D: 4}, count: 3},
  {scores: {A: 0, B: 0, C: 4, D: 5}, count: 1},
];
function request(method: Method): ElectionRequest {
  const ballots: Ballot[] = method === 'sortition' ? [] : ['approval', 'proportional-approval', 'sequential-proportional-approval', 'phragmen'].includes(method) ? approved : method === 'reweighted-range' ? scores : method === 'limited-vote' ? [
    {approvals: ['A'], count: 6}, {approvals: ['C'], count: 3}, {approvals: ['D'], count: 1},
  ] : method === 'cumulative' ? [
    {votes: {A: 60, B: 40, C: 0, D: 0}, count: 6},
    {votes: {A: 0, B: 0, C: 60, D: 40}, count: 3},
    {votes: {A: 0, B: 0, C: 0, D: 100}, count: 1},
  ] : ranked;
  return {method, candidates, seats: 2, ballots};
}
const expected: Record<Method, string[]> = {
  'approval': ['A', 'B'], 'proportional-approval': ['A', 'D'],
  'sequential-proportional-approval': ['A', 'D'], 'reweighted-range': ['A', 'C'],
  'stv': ['A', 'C'], 'cpo-stv': ['A', 'C'], 'schulze-stv': ['A', 'C'],
  'phragmen': ['A', 'D'], 'k-borda': ['A', 'C'], 'bloc': ['A', 'B'],
  'quota-borda': ['A', 'C'], 'expanding-approvals': ['A', 'C'],
  'minimax': ['A', 'C'], 'minimax-external-opposition': ['A', 'B'],
  'single-non-transferable': ['A', 'C'], 'limited-vote': ['A', 'C'],
  'cumulative': ['A', 'B'], 'sortition': ['A', 'C'], 'multiple-random-ballots': ['A', 'B'],
};
for (const method of METHODS) {
  const counted = simulate(request(method));
  assert.deepEqual(counted.winners, expected[method], method);
  assert.equal(counted.winners.length, 2);
  assert.equal(counted.seats, 2);
  assert.ok(counted.trace.length > 0);
}

// A committee is an ordinary result, not automatically an unresolved tie.
assert.equal(simulate(request('bloc')).tie, false);
assert.equal(simulate(request('sequential-proportional-approval')).tie, true);
assert.deepEqual(simulate(request('k-borda')).trace[0].tally, {A: 21, B: 13, C: 17, D: 9});
assert.deepEqual(simulate(request('approval')).trace[0].tally, {A: 6, B: 6, C: 3, D: 4});

// Exact fractional surplus: A retains four of its six votes, transferring two.
const stv = simulate(request('stv'));
assert.equal(stv.trace[0].quota, 4);
assert.equal(stv.trace[1].transferFactor, 1 / 3);
assert.deepEqual(stv.trace[2].tally, {B: 2, C: 3, D: 1});
assert.equal(stv.trace[2].eliminated, 'D');

// Compare committees A-C and A-B after removing D and transferring common A.
const cpo = simulate(request('cpo-stv'));
const cpoSupport = cpo.trace[0].support as number[][];
assert.equal(cpoSupport[1][0], 8);
assert.equal(cpoSupport[0][1], 6);
// Weighted Hall constraints give min(A support9,C support4,union support10/2)=4.
const schulze = simulate(request('schulze-stv'));
const links = schulze.trace[0].links as number[][];
assert.equal(links[1][0], 4);
assert.equal(links[0][1], 3);

// The published Schulze STV rule has a third stage after committee paths.
// Stage two leaves A-B and B-D tied; the single-winner relation removes B-D.
const stageThree = simulate({method: 'schulze-stv', candidates, seats: 2, ballots: [
  {ranking: ['A', 'B', 'D', 'C']}, {ranking: ['B', 'A', 'D', 'C'], count: 3},
  {ranking: ['D', 'C', 'B', 'A'], count: 2},
]});
assert.deepEqual(stageThree.trace[0].stageTwoCommittees, [['A', 'B'], ['B', 'D']]);
assert.deepEqual(stageThree.winners, ['A', 'B']);
assert.equal(stageThree.tie, false);

// Distinguish ranking individuals from optimizing a committee's external score.
const unanimous = {candidates: ['A', 'B', 'C'], seats: 2, ballots: [{ranking: ['A', 'B', 'C'], count: 3}]};
const simpson = simulate({...unanimous, method: 'minimax'});
assert.deepEqual(simpson.trace[1].simpsonScores, {A: 3, B: 0, C: 0});
assert.equal(simpson.tie, true);
assert.deepEqual(simulate({...unanimous, method: 'minimax-external-opposition'}).winners, ['A', 'B']);
assert.equal(simulate({...unanimous, method: 'minimax-external-opposition'}).tie, false);

// Brute harmonic utility oracle: the engine's selected committee attains the
// largest independently computed utility over all pairs on this profile.
const pav = simulate(request('proportional-approval'));
function utility(committee: string[]): number {
  return approved.reduce((sum, b) => {
    const count = committee.filter(c => b.approvals.includes(c)).length;
    let harmonic = 0; for (let i = 1; i <= count; i++) harmonic += 1 / i;
    return sum + b.count * harmonic;
  }, 0);
}
const pairScores: number[] = [];
for (let i = 0; i < candidates.length; i++) for (let j = i + 1; j < candidates.length; j++) pairScores.push(utility([candidates[i], candidates[j]]));
assert.equal(utility(pav.winners), Math.max(...pairScores));
assert.equal(utility(['A', 'B']), 9);
assert.equal(utility(['A', 'D']), 10);

// Unsupported candidates are valid: priority fills remaining seats, and null
// load levels are JSON data rather than Infinity or NaN.
const noSupport = simulate({method: 'phragmen', candidates: ['A', 'B', 'C'], seats: 2, ballots: [{approvals: []}]});
assert.deepEqual(noSupport.winners, ['A', 'B']);
assert.deepEqual(noSupport.trace[0].loadLevels, {A: null, B: null, C: null});
assert.equal(noSupport.tie, true);
assert.doesNotThrow(() => JSON.parse(JSON.stringify(noSupport)));

// The seeded draw changes state between seats, never samples one name twice.
for (const method of ['sortition', 'multiple-random-ballots'] as Method[]) {
  const value = simulate(request(method));
  assert.equal(value.trace[0].state, 1015568748);
  assert.equal(value.trace[1].state, 1586005467);
  assert.equal(new Set(value.winners).size, 2);
  assert.deepEqual(value, simulate(request(method)));
}

// Names with prototype meaning remain ordinary own data keys in every method.
const names = ['__proto__', 'constructor', 'toString'];
for (const method of METHODS) {
  let ballots: Ballot[] = [{ranking: names, count: 3}];
  if (['approval', 'proportional-approval', 'sequential-proportional-approval', 'phragmen', 'limited-vote'].includes(method)) ballots = [{approvals: ['__proto__'], count: 3}];
  if (method === 'reweighted-range') ballots = [{scores: Object.fromEntries(names.map((c, i) => [c, 5 - i]))}];
  if (method === 'cumulative') ballots = [{votes: Object.fromEntries(names.map((c, i) => [c, 5 - i]))}];
  if (method === 'sortition') ballots = [];
  const value = simulate({method, candidates: names, seats: 2, ballots});
  assert.equal(value.winners.length, 2, method);
  assert.ok(value.winners.every(c => names.includes(c)));
}

for (const invalid of [
  {...request('k-borda'), seats: 0}, {...request('k-borda'), seats: 5},
  {...request('k-borda'), seats: true}, {...request('k-borda'), ballots: [{ranking: ['A', 'B']}]},
  {...request('reweighted-range'), ballots: [{scores: {A: 6, B: 0, C: 0, D: 0}}]},
  {...request('limited-vote'), options: {limit: 2}},
  {...request('limited-vote'), ballots: [{approvals: ['A', 'B']}]},
  {...request('cumulative'), ballots: [{votes: {A: 101, B: 0, C: 0, D: 0}}]},
]) assert.throws(() => simulate(invalid), ElectionError);
const tooMany = Array.from({length: 7}, (_, i) => String(i));
for (const method of ['cpo-stv', 'schulze-stv']) {
  assert.throws(() => simulate({method, candidates: tooMany, seats: 3, ballots: [{ranking: tooMany}]}),
    (error: unknown) => error instanceof ElectionError && error.status === 413);
}
console.log('PASS: 19 TypeScript multi-winner methods, exact transfer and support fixtures, committee optimization, seeded draws, ties, identifiers, and resource guards');
