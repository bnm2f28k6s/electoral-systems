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

function median(histogram: number[]): number {
  const position = Math.floor((histogram.reduce((a, b) => a + b, 0) - 1) / 2);
  let cumulative = 0;
  for (let grade = 0; grade < histogram.length; grade++) {
    cumulative += histogram[grade];
    if (cumulative > position) return grade;
  }
  return -1;
}

export function countMajorityJudgment(ctx: Context): SimulationResult {
  const histograms = Object.fromEntries(ctx.candidates.map(c => [c, Array(ctx.maxScore + 1).fill(0) as number[]]));
  for (const b of ctx.ballots) for (const c of ctx.candidates) histograms[c][b.scores![c]] += b.count;
  const initial = Object.fromEntries(ctx.candidates.map(c => [c, median(histograms[c])]));
  const trace: Trace = [{majorityGrades: initial, histograms: Object.fromEntries(ctx.candidates.map(c => [c, [...histograms[c]]]))}];
  let active = best(ctx.candidates, initial);
  let removed = 0;
  while (active.length > 1 && histograms[active[0]].reduce((a, b) => a + b, 0) > 0) {
    if (active.every(c => histograms[c].every((v, i) => v === histograms[active[0]][i]))) break;
    // Batch exactly the removals until at least one tied candidate's median changes.
    const batch = Math.min(...active.map(c => {
      const h = histograms[c], grade = median(h);
      const n = h.reduce((a, b) => a + b, 0);
      const below = h.slice(0, grade).reduce((a, b) => a + b, 0);
      return Math.min(n - 1 - 2 * below, 2 * below + 2 * h[grade] - n) + 1;
    }));
    for (const c of active) histograms[c][median(histograms[c])] -= batch;
    removed += batch;
    const grades = Object.fromEntries(active.map(c => [c, median(histograms[c])]));
    active = best(active, grades);
  }
  trace.push({medianGradesRemoved: removed, remaining: active});
  return result(ctx, active, trace);
}

const election: Context = {
  "method": "majority-judgment",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "scores": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 5
      },
      "count": 2
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 9
};
console.log(JSON.stringify(countMajorityJudgment(election), null, 2));
