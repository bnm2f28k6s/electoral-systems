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

function zeros(candidates: string[]): Tally {return Object.fromEntries(candidates.map(c => [c, 0]));}

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function pairwise(ctx: Context): Matrix {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const ballot of ctx.ballots) {
    const ranking = ballot.ranking!;
    ranking.forEach((a, index) => {for (const b of ranking.slice(index + 1)) matrix[a][b] += ballot.count;});
  }
  return matrix;
}

function* combinations<T>(items: T[], k: number, start = 0, prefix: T[] = []): Generator<T[]> {
  if (!k) {yield prefix; return;}
  for (let i = start; i <= items.length - k; i++) yield* combinations(items, k - 1, i + 1, [...prefix, items[i]]);
}

function schulzeStrength(ctx: Context, committee: string[], outsider: string): Fraction {
  let strength: Fraction | null = null;
  for (let size = 1; size <= committee.length; size++) for (const subset of combinations(committee, size)) {
    const support = ctx.ballots.reduce((sum, b) => sum + (subset.some(c => b.ranking!.indexOf(c) < b.ranking!.indexOf(outsider)) ? b.count : 0), 0);
    const value = fraction(support, size);
    if (strength === null || compare(value, strength) < 0) strength = value;
  }
  return strength!;
}

export function countSchulzeStv(ctx: Context): SimulationResult {
  const committees = [...combinations(ctx.candidates, ctx.seats)], n = committees.length;
  const links = committees.map(() => committees.map(() => fraction(0)));
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const outsiders = committees[j].filter(c => !committees[i].includes(c));
    if (outsiders.length === 1) links[i][j] = schulzeStrength(ctx, committees[i], outsiders[0]);
  }
  const paths = links.map(row => [...row]);
  for (let middle = 0; middle < n; middle++) for (let start = 0; start < n; start++) for (let end = 0; end < n; end++) {
    if (new Set([middle, start, end]).size === 3) {
      const strength = compare(paths[start][middle], paths[middle][end]) < 0 ? paths[start][middle] : paths[middle][end];
      if (compare(strength, paths[start][end]) > 0) paths[start][end] = strength;
    }
  }
  const stageTwoCommittees = committees.filter((_, i) => paths[i].every((strength, j) => compare(strength, paths[j][i]) >= 0));
  const singleWinnerPaths = pairwise(ctx);
  for (const middle of ctx.candidates) for (const start of ctx.candidates) for (const end of ctx.candidates) {
    if (new Set([middle, start, end]).size === 3) singleWinnerPaths[start][end] = Math.max(singleWinnerPaths[start][end], Math.min(singleWinnerPaths[start][middle], singleWinnerPaths[middle][end]));
  }
  const tied = stageTwoCommittees.filter(second => !stageTwoCommittees.some(first => first !== second && first.filter(c => !second.includes(c)).some(a => second.filter(c => !first.includes(c)).every(b => singleWinnerPaths[a][b] > singleWinnerPaths[b][a]))));
  return result(ctx, tied[0], tied.length > 1, [{committees, links: links.map(row => row.map(asNumber)), strongestPaths: paths.map(row => row.map(asNumber)), stageTwoCommittees, singleWinnerPaths, tiedCommittees: tied}]);
}

const election: Context = {
  "method": "schulze-stv",
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
console.log(JSON.stringify(countSchulzeStv(election), null, 2));
