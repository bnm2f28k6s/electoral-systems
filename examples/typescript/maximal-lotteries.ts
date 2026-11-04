// Node 22.18+ (native TypeScript). Save as example.ts; run: node example.ts
// Self-contained count for valid input; the API also validates requests.
export const METHODS = [
  'plurality', 'anti-plurality', 'two-round', 'instant-runoff', 'coombs',
  'nanson', 'baldwin', 'tideman-alternative', 'minimax', 'copeland', 'black',
  'kemeny-young', 'ranked-pairs', 'schulze', 'borda', 'bucklin', 'dodgson',
  'approval', 'majority-judgment', 'score', 'star', 'quadratic', 'random-ballot',
  'maximal-lotteries', 'sortition',
] as const;
export type Method = typeof METHODS[number];
export type Ballot = { count?: number; ranking?: string[]; choice?: string;
  approvals?: string[]; scores?: Record<string, number>; credits?: Record<string, number> };
export type ElectionRequest = { method: Method; candidates: string[]; ballots: Ballot[];
  options?: { maxScore?: number; budget?: number; seed?: number } };
export type Trace = Record<string, unknown>[];
export type SimulationResult = { method: Method; winners: string[]; tie: boolean;
  trace: Trace; lottery?: { candidate: string; probability: number }[] };
type Context = { method: Method; candidates: string[]; ballots: (Ballot & {count: number})[];
  maxScore: number; budget: number; seed: number; total: number };
type Tally = Record<string, number>;
type Pairwise = Record<string, Tally>;
type Fraction = [bigint, bigint];
export class ElectionError extends Error {
  status: number;
  constructor(message: string, status = 400) { super(message); this.name = 'ElectionError'; this.status = status; }
}

function zeros(candidates: string[]): Tally { return Object.fromEntries(candidates.map(c => [c, 0])); }

function result(ctx: Context, winners: string[], trace: Trace, lottery?: number[]): SimulationResult {
  const ordered = ctx.candidates.filter(c => winners.includes(c));
  const answer: SimulationResult = { method: ctx.method, winners: ordered, tie: ordered.length > 1, trace };
  if (lottery) answer.lottery = ctx.candidates.map((candidate, i) => ({candidate, probability: lottery[i]}));
  return answer;
}

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

function randomUnit(seed: number): number { return ((Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296; }

function sample(probabilities: number[], seed: number): number {
  const draw = randomUnit(seed);
  let cumulative = 0;
  for (let i = 0; i < probabilities.length; i++) { cumulative += probabilities[i]; if (draw < cumulative) return i; }
  return probabilities.length - 1;
}

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

function multiply(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[0], a[1] * b[1]); }

function negate(a: Fraction): Fraction { return [-a[0], a[1]]; }

function divide(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1], a[1] * b[0]); }

function gaussian(rows: number[][], rhs: number[]): Fraction[] | null {
  const n = rows.length;
  const a = rows.map((row, i) => [...row.map(v => fraction(BigInt(v))), fraction(BigInt(rhs[i]))]);
  for (let col = 0; col < n; col++) {
    const pivot = a.findIndex((row, i) => i >= col && row[col][0] !== 0n);
    if (pivot < 0) return null;
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const divisor = a[col][col];
    a[col] = a[col].map(v => divide(v, divisor));
    for (let i = 0; i < n; i++) if (i !== col) {
      const factor = a[i][col];
      a[i] = a[i].map((v, j) => add(v, negate(multiply(factor, a[col][j]))));
    }
  }
  return a.map(row => row[n]);
}

function* combinations(n: number, k: number, start = 0, prefix: number[] = []): Generator<number[]> {
  if (!k) { yield prefix; return; }
  for (let i = start; i <= n - k; i++) yield* combinations(n, k - 1, i + 1, [...prefix, i]);
}

export function countMaximalLotteries(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const n = ctx.candidates.length;
  const margins = ctx.candidates.map(c => ctx.candidates.map(d => matrix[c][d] - matrix[d][c]));
  const constraints = [
    ...ctx.candidates.map((_, i) => ctx.candidates.map((_, j) => i === j ? 1 : 0)),
    ...ctx.candidates.map((_, j) => ctx.candidates.map((_, i) => margins[i][j])),
  ];
  for (const active of combinations(2 * n, n - 1)) {
    const p = gaussian([Array(n).fill(1), ...active.map(i => constraints[i])], [1, ...active.map(() => 0)]);
    if (!p || p.some(v => v[0] < 0n)) continue;
    const feasible = constraints.slice(n).every(row => row.reduce((s, v, i) => add(s, multiply(fraction(BigInt(v)), p[i])), fraction(0n))[0] >= 0n);
    if (!feasible) continue;
    const probabilities = p.map(v => Number(v[0]) / Number(v[1]));
    const chosen = sample(probabilities, ctx.seed);
    return result(ctx, [ctx.candidates[chosen]], [{pairwise: matrix}, {margins, seed: ctx.seed}], probabilities);
  }
  throw new ElectionError('No maximal lottery found', 500);
}

const election: Context = {
  "method": "maximal-lotteries",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C"
      ],
      "count": 4
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 3
    },
    {
      "ranking": [
        "C",
        "B",
        "A"
      ],
      "count": 2
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 9
};
console.log(JSON.stringify(countMaximalLotteries(election), null, 2));
