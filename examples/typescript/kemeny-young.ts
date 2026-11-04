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

function* permutations<T>(items: T[]): Generator<T[]> {
  if (!items.length) { yield []; return; }
  for (let i = 0; i < items.length; i++) for (const rest of permutations(items.filter((_, j) => j !== i))) yield [items[i], ...rest];
}

export function countKemenyYoung(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  let maximum = -1;
  let order: string[] = [];
  let optimalOrders = 0;
  const leaders = new Set<string>();
  for (const ranking of permutations(ctx.candidates)) {
    let score = 0;
    for (let i = 0; i < ranking.length; i++) for (let j = i + 1; j < ranking.length; j++) score += matrix[ranking[i]][ranking[j]];
    if (score > maximum) { maximum = score; order = ranking; leaders.clear(); optimalOrders = 0; }
    if (score === maximum) { leaders.add(ranking[0]); optimalOrders++; }
  }
  return result(ctx, ctx.candidates.filter(c => leaders.has(c)), [{pairwise: matrix}, {bestScore: maximum, optimalOrders, ranking: order}]);
}

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

const election: Context = {
  "method": "kemeny-young",
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
console.log(JSON.stringify(countKemenyYoung(election), null, 2));
