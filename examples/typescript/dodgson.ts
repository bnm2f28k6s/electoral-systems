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

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

export function countDodgson(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const tally = zeros(ctx.candidates);
  const rankings = ctx.ballots.flatMap(b => Array.from({length: b.count}, () => b.ranking!));
  for (const candidate of ctx.candidates) {
    const opponents = ctx.candidates.filter(c => c !== candidate);
    const need = opponents.map(c => Math.max(0, Math.floor(ctx.total / 2) + 1 - matrix[candidate][c]));
    const target = need.join(',');
    let dp = new Map<string, number>([[need.map(() => 0).join(','), 0]]);
    for (const ranking of rankings) {
      const next = new Map<string, number>();
      const pos = ranking.indexOf(candidate);
      for (const [key, cost] of dp) {
        const gained = key ? key.split(',').map(Number) : [];
        for (let promotion = 0; promotion <= pos; promotion++) {
          const crossed = ranking.slice(pos - promotion, pos);
          const updated = gained.map((v, i) => Math.min(need[i], v + (crossed.includes(opponents[i]) ? 1 : 0))).join(',');
          next.set(updated, Math.min(next.get(updated) ?? Infinity, cost + promotion));
        }
      }
      dp = next;
    }
    tally[candidate] = dp.get(target)!;
  }
  return result(ctx, best(ctx.candidates, tally, true), [{pairwise: matrix}, {adjacentSwaps: tally}]);
}

const election: Context = {
  "method": "dodgson",
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
      "count": 3
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 2
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
  "total": 7
};
console.log(JSON.stringify(countDodgson(election), null, 2));
