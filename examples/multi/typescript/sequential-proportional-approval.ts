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

function sequential(ctx: Context, mode: 'sequential-proportional-approval' | 'reweighted-range'): SimulationResult {
  const elected: string[] = [], trace: Trace = [];
  let tie = false;
  while (elected.length < ctx.seats) {
    const candidates = ctx.candidates.filter(c => !elected.includes(c));
    const tally = Object.fromEntries(candidates.map(c => [c, fraction(0)]));
    for (const ballot of ctx.ballots) {
      const represented = mode === 'sequential-proportional-approval' ? elected.filter(c => ballot.approvals!.includes(c)).length : elected.reduce((sum, c) => sum + ballot.scores![c], 0);
      for (const c of candidates) {
        const increment = mode === 'sequential-proportional-approval' ? (ballot.approvals!.includes(c) ? fraction(ballot.count, 1 + represented) : fraction(0)) : fraction(ballot.count * ballot.scores![c] * ctx.maxScore, ctx.maxScore + represented);
        tally[c] = add(tally[c], increment);
      }
    }
    let high = tally[candidates[0]];
    for (const c of candidates) if (compare(tally[c], high) > 0) high = tally[c];
    const tied = candidates.filter(c => compare(tally[c], high) === 0);
    const selected = tied[0]; tie ||= tied.length > 1;
    const row: Record<string, unknown> = {round: elected.length + 1, tally: Object.fromEntries(candidates.map(c => [c, asNumber(tally[c])])), selected, tied};
    if (mode === 'reweighted-range') row.weights = ctx.ballots.map(b => asNumber(fraction(ctx.maxScore, ctx.maxScore + elected.reduce((sum, c) => sum + b.scores![c], 0))));
    trace.push(row);
    elected.push(selected);
  }
  return result(ctx, elected, tie, trace);
}

export function countSequentialProportionalApproval(ctx: Context): SimulationResult {return sequential(ctx, 'sequential-proportional-approval');}

const election: Context = {
  "method": "sequential-proportional-approval",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "approvals": [
        "A",
        "B"
      ],
      "count": 6
    },
    {
      "approvals": [
        "C",
        "D"
      ],
      "count": 3
    },
    {
      "approvals": [
        "D"
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
console.log(JSON.stringify(countSequentialProportionalApproval(election), null, 2));
