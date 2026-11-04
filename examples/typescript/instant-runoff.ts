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

function best(candidates: string[], tally: Tally, minimize = false): string[] {
  const optimum = (minimize ? Math.min : Math.max)(...candidates.map(c => tally[c]));
  return candidates.filter(c => tally[c] === optimum);
}

function firstCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) tally[b.ranking!.find(c => active.includes(c))!] += b.count;
  return tally;
}

function bordaCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) {
    const order = b.ranking!.filter(c => active.includes(c));
    order.forEach((c, i) => { tally[c] += (active.length - 1 - i) * b.count; });
  }
  return tally;
}

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

function smith(active: string[], matrix: Pairwise): string[] {
  let smallest = active;
  for (const start of active) {
    const set = new Set([start]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const d of active) if (!set.has(d) && [...set].some(c => matrix[c][d] <= matrix[d][c])) { set.add(d); changed = true; }
    }
    if (set.size < smallest.length) smallest = active.filter(c => set.has(c));
  }
  return smallest;
}

function elimination(ctx: Context, mode: string): SimulationResult {
  let active = [...ctx.candidates];
  const trace: Trace = [];
  const matrix = mode === 'tideman-alternative' ? pairwise(ctx) : null;
  while (active.length > 1) {
    if (matrix) {
      const smithSet = smith(active, matrix);
      if (smithSet.length !== active.length) {
        trace.push({active: [...active], smith: smithSet});
        active = smithSet;
        if (active.length === 1) break;
      }
    }
    const first = firstCounts(ctx, active);
    if (['instant-runoff', 'coombs', 'tideman-alternative'].includes(mode)) {
      const majority = active.filter(c => first[c] * 2 > ctx.total);
      if (majority.length) { trace.push({active: [...active], tally: first}); return result(ctx, majority, trace); }
    }
    let tally = first;
    let worst: string[];
    if (mode === 'coombs') {
      tally = zeros(active);
      for (const b of ctx.ballots) tally[b.ranking!.filter(c => active.includes(c)).at(-1)!] += b.count;
      worst = best(active, tally);
    } else if (['nanson', 'baldwin'].includes(mode)) {
      tally = bordaCounts(ctx, active);
      worst = best(active, tally, true);
    } else worst = best(active, tally, true);
    const row: Record<string, unknown> = {active: [...active], tally};
    if (new Set(Object.values(tally)).size === 1 && (mode === 'nanson' || active.length === 2)) { trace.push(row); return result(ctx, active, trace); }
    const eliminated = mode === 'nanson'
      ? active.filter(c => tally[c] * active.length <= Object.values(tally).reduce((a, b) => a + b, 0))
      : [worst.at(-1)!];
    row.eliminated = eliminated;
    trace.push(row);
    active = active.filter(c => !eliminated.includes(c));
  }
  trace.push({active: [...active]});
  return result(ctx, active, trace);
}

export function countInstantRunoff(ctx: Context): SimulationResult { return elimination(ctx, 'instant-runoff'); }

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

const election: Context = {
  "method": "instant-runoff",
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
console.log(JSON.stringify(countInstantRunoff(election), null, 2));
