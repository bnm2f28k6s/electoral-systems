// Node 22.18+. Save as example.ts and run: node example.ts
// Complete count for valid input. The API performs full validation.
export const METHODS = [
  'approval', 'proportional-approval', 'sequential-proportional-approval',
  'reweighted-range', 'stv', 'cpo-stv', 'schulze-stv', 'phragmen', 'k-borda',
  'bloc', 'quota-borda', 'expanding-approvals', 'minimax',
  'minimax-external-opposition', 'single-non-transferable', 'limited-vote',
  'cumulative', 'sortition', 'multiple-random-ballots',
] as const;
export type Method = typeof METHODS[number];
export type Ballot = { count?: number; ranking?: string[]; approvals?: string[];
  choice?: string; scores?: Record<string, number>; votes?: Record<string, number> };
export type ElectionRequest = { method: Method; candidates: string[]; seats: number;
  ballots: Ballot[]; options?: {maxScore?: number; budget?: number; limit?: number; seed?: number} };
export type Trace = Record<string, unknown>[];
export type SimulationResult = {method: Method; seats: number; winners: string[]; tie: boolean; trace: Trace};
type Context = {method: Method; candidates: string[]; seats: number; ballots: (Ballot & {count: number})[];
  maxScore: number; budget: number; limit: number; seed: number; total: number};
type Tally = Record<string, number>;
type Matrix = Record<string, Tally>;
type Fraction = [bigint, bigint];
export class ElectionError extends Error {
  status: number;
  constructor(message: string, status = 400) {super(message); this.name = 'ElectionError'; this.status = status;}
}

function integer(value: unknown, low: number, high: number, name: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < low || value > high)
    throw new ElectionError(`${name} must be an integer from ${low} to ${high}`);
  return value;
}

function gcd(a: bigint, b: bigint): bigint {while (b) {const next = b; b = a % b; a = next;} return a < 0n ? -a : a;}

function fraction(n: number | bigint, d: number | bigint = 1): Fraction {
  let a = BigInt(n), b = BigInt(d); if (b < 0n) {a = -a; b = -b;} const g = gcd(a, b); return [a / g, b / g];
}

function add(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);}

function negate(a: Fraction): Fraction {return [-a[0], a[1]];}

function subtract(a: Fraction, b: Fraction): Fraction {return add(a, negate(b));}

function multiply(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[0], a[1] * b[1]);}

function divide(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1], a[1] * b[0]);}

function compare(a: Fraction, b: Fraction): number {const d = a[0] * b[1] - b[0] * a[1]; return d < 0n ? -1 : d > 0n ? 1 : 0;}
/** Round an exact rational to a JSON-display number without BigInt overflow.
 * Election decisions use compare(), never this floating-point conversion.
 */

export function asNumber(a: Fraction): number {
  let numerator = a[0], denominator = a[1];
  if (denominator === 0n) throw new RangeError('A rational denominator cannot be zero');
  const negative = (numerator < 0n) !== (denominator < 0n);
  if (numerator < 0n) numerator = -numerator;
  if (denominator < 0n) denominator = -denominator;
  if (numerator === 0n) return 0;
  // Determine the binary exponent while retaining all integer precision.
  let exponent = numerator.toString(2).length - denominator.toString(2).length;
  if (exponent >= 0 ? numerator < (denominator << BigInt(exponent)) : (numerator << BigInt(-exponent)) < denominator) exponent--;
  if (exponent > 1023) return negative ? -Infinity : Infinity;
  // Normal doubles have 53 significant bits; subnormals use units of 2^-1074.
  const shift = exponent < -1022 ? 1074 : 52 - exponent;
  const top = shift >= 0 ? numerator << BigInt(shift) : numerator;
  const bottom = shift >= 0 ? denominator : denominator << BigInt(-shift);
  let significant = top / bottom;
  const remainder = top % bottom;
  // IEEE-754 round-to-nearest, choosing the even significand at an exact tie.
  if (2n * remainder > bottom || (2n * remainder === bottom && significant % 2n === 1n)) significant++;
  const value = Number(significant) * (exponent < -1022 ? Number.MIN_VALUE : 2 ** (exponent - 52));
  return negative ? -value : value;
}

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function* combinations<T>(items: T[], k: number, start = 0, prefix: T[] = []): Generator<T[]> {
  if (!k) {yield prefix; return;}
  for (let i = start; i <= items.length - k; i++) yield* combinations(items, k - 1, i + 1, [...prefix, items[i]]);
}

function optimize(ctx: Context, scorer: (committee: string[]) => Fraction, prefix: Trace = [], minimize = false): SimulationResult {
  let optimum: Fraction | null = null;
  const tied: string[][] = [];
  const scores: {committee: string[]; score: number}[] = [];
  for (const committee of combinations(ctx.candidates, ctx.seats)) {
    const score = scorer(committee);
    scores.push({committee, score: asNumber(score)});
    const comparison = optimum === null ? (minimize ? -1 : 1) : compare(score, optimum);
    if ((minimize ? -comparison : comparison) > 0) {optimum = score; tied.length = 0; tied.push(committee);}
    else if (comparison === 0) tied.push(committee);
  }
  return result(ctx, tied[0], tied.length > 1,
    [...prefix, {committees: scores, bestScore: asNumber(optimum!), tiedCommittees: tied}]);
}

function cpoSupport(ctx: Context, first: string[], second: string[], quota: number, decisions: Trace = []): [Fraction, Fraction] {
  const active = ctx.candidates.filter(c => first.includes(c) || second.includes(c));
  const common = ctx.candidates.filter(c => first.includes(c) && second.includes(c));
  let weights = ctx.ballots.map(b => fraction(b.count)), retained = fraction(0);
  let tally: Record<string, Fraction> = {};
  while (true) {
    const choices = ctx.ballots.map(b => b.ranking!.find(c => active.includes(c))!);
    tally = Object.fromEntries(active.map(c => {
      let score = fraction(0); choices.forEach((choice, i) => {if (choice === c) score = add(score, weights[i]);}); return [c, score];
    }));
    const eligible = common.filter(c => active.includes(c) && compare(tally[c], fraction(quota)) > 0);
    if (!eligible.length) break;
    let winner = eligible[0];
    for (const c of eligible) if (compare(tally[c], tally[winner]) > 0) winner = c;
    const tied = eligible.filter(c => compare(tally[c], tally[winner]) === 0);
    if (tied.length > 1) decisions.push({candidates: tied, selected: winner});
    const factor = divide(subtract(tally[winner], fraction(quota)), tally[winner]);
    weights = weights.map((w, i) => choices[i] === winner ? multiply(w, factor) : w);
    retained = add(retained, fraction(quota)); active.splice(active.indexOf(winner), 1);
  }
  let left = retained, right = retained;
  for (const c of active) {if (first.includes(c)) left = add(left, tally[c]); if (second.includes(c)) right = add(right, tally[c]);}
  return [left, right];
}

export function countCpoStv(ctx: Context): SimulationResult {
  const committees = [...combinations(ctx.candidates, ctx.seats)];
  const quota = Math.floor(ctx.total / (ctx.seats + 1)) + 1;
  const support = committees.map(() => committees.map(() => fraction(0)));
  const comparisonTies: Trace = [];
  for (let i = 0; i < committees.length; i++) for (let j = i + 1; j < committees.length; j++) {
    const decisions: Trace = [];
    [support[i][j], support[j][i]] = cpoSupport(ctx, committees[i], committees[j], quota, decisions);
    if (decisions.length) comparisonTies.push({first: committees[i], second: committees[j], decisions});
  }
  const worst = committees.map((_, i) => {
    let value = fraction(0);
    for (let j = 0; j < committees.length; j++) if (i !== j) {const loss = subtract(support[j][i], support[i][j]); if (compare(loss, value) > 0) value = loss;}
    return value;
  });
  const answer = optimize(ctx, committee => worst[committees.findIndex(other => other.every((c, i) => c === committee[i]))],
    [{quota, support: support.map(row => row.map(asNumber)), comparisonTies}], true);
  answer.tie ||= comparisonTies.length > 0;
  return answer;
}

const election: Context = {
  "method": "cpo-stv",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C",
        "D"
      ],
      "count": 6
    },
    {
      "ranking": [
        "C",
        "D",
        "A",
        "B"
      ],
      "count": 3
    },
    {
      "ranking": [
        "D",
        "C",
        "B",
        "A"
      ],
      "count": 1
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "limit": 1,
  "seed": 1,
  "total": 10
};
console.log(JSON.stringify(countCpoStv(election), null, 2));
