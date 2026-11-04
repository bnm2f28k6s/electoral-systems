/** Single-winner teaching algorithms, with strict inputs and inspectable counts.
 * No imports or runtime dependencies. Node 22.18+ can execute this TypeScript.
 * Matching Python implementation: python/electoral.py.
 */

// BEGIN shared
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
// END shared

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function integer(value: unknown, minimum: number, maximum: number, name: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum || value > maximum)
    throw new ElectionError(`${name} must be an integer from ${minimum} to ${maximum}`);
  return value;
}

function exactKeys(value: Record<string, unknown>, allowed: string[], name: string): void {
  if (Object.keys(value).some(k => !allowed.includes(k))) throw new ElectionError(`Unknown field in ${name}`);
}

export function normalize(input: unknown): Context {
  if (!object(input)) throw new ElectionError('Request must be an object');
  exactKeys(input, ['method', 'candidates', 'ballots', 'options'], 'request');
  if (!(METHODS as readonly unknown[]).includes(input.method)) throw new ElectionError('Unknown method');
  const method = input.method as Method;
  const candidates = input.candidates;
  if (!Array.isArray(candidates) || !candidates.length || candidates.some(c => typeof c !== 'string' || !c.trim() || [...c].length > 100) || new Set(candidates).size !== candidates.length)
    throw new ElectionError('candidates must be unique nonempty strings');
  if (candidates.length > 32) throw new ElectionError('At most 32 candidates are supported', 413);
  if (!Array.isArray(input.ballots)) throw new ElectionError('ballots must be an array');
  if (input.ballots.length > 10000) throw new ElectionError('At most 10000 ballot groups are supported', 413);
  const opts = Object.hasOwn(input, 'options') ? input.options : {};
  if (!object(opts)) throw new ElectionError('options must be an object');
  exactKeys(opts, ['maxScore', 'budget', 'seed'], 'options');
  const maxScore = integer(Object.hasOwn(opts, 'maxScore') ? opts.maxScore : 5, 1, 100, 'maxScore');
  const budget = integer(Object.hasOwn(opts, 'budget') ? opts.budget : 100, 1, 1000000, 'budget');
  const seed = integer(Object.hasOwn(opts, 'seed') ? opts.seed : 1, 0, 4294967295, 'seed');
  let total = 0;
  const ballots = input.ballots.map((b: unknown) => {
    if (!object(b)) throw new ElectionError('Each ballot must be an object');
    exactKeys(b, ['count', 'ranking', 'choice', 'approvals', 'scores', 'credits'], 'ballot');
    const count = integer(Object.hasOwn(b, 'count') ? b.count : 1, 1, 1000000, 'count');
    total += count;
    const fields = ['ranking', 'choice', 'approvals', 'scores', 'credits'].filter(k => k in b);
    if (fields.length !== 1) throw new ElectionError('Each ballot must have exactly one ballot format');
    const field = fields[0];
    const single = ['plurality', 'anti-plurality', 'random-ballot'].includes(method);
    const expected = method === 'approval' ? 'approvals' : ['score', 'star', 'majority-judgment'].includes(method) ? 'scores' : method === 'quadratic' ? 'credits' : 'ranking';
    if (!(single ? ['ranking', 'choice'].includes(field) : field === expected)) throw new ElectionError(`Wrong ballot format for ${method}`);
    if (field === 'ranking') {
      if (!Array.isArray(b.ranking) || b.ranking.length !== candidates.length || new Set(b.ranking).size !== candidates.length || b.ranking.some(c => !candidates.includes(c)))
        throw new ElectionError('ranking must list every candidate exactly once');
    } else if (field === 'choice') {
      if (!candidates.includes(b.choice)) throw new ElectionError('choice must name a candidate');
    } else if (field === 'approvals') {
      if (!Array.isArray(b.approvals) || new Set(b.approvals).size !== b.approvals.length || b.approvals.some(c => !candidates.includes(c)))
        throw new ElectionError('approvals must be a subset of candidates without duplicates');
    } else {
      const values = b[field];
      if (!object(values) || Object.keys(values).length !== candidates.length || candidates.some(c => !Object.hasOwn(values, c)))
        throw new ElectionError(`${field} must contain every candidate exactly once`);
      for (const c of candidates) integer(values[c], field === 'credits' ? -1000 : 0, field === 'credits' ? 1000 : maxScore, field);
      if (field === 'credits' && Object.values(values).reduce((s: number, v: any) => s + v * v, 0) > budget)
        throw new ElectionError('Quadratic ballot exceeds its credit budget');
    }
    return { ...b, count } as Ballot & {count: number};
  });
  if (total > 1000000) throw new ElectionError('At most 1000000 total ballots are supported', 413);
  if (method === 'sortition') {
    if (ballots.length) throw new ElectionError('Sortition takes no ballots');
  } else if (!total) throw new ElectionError('At least one ballot is required');
  if (method === 'kemeny-young' && candidates.length > 8) throw new ElectionError('Kemeny-Young supports at most 8 candidates', 413);
  if (method === 'dodgson' && (candidates.length > 5 || total > 8)) throw new ElectionError('Dodgson supports at most 5 candidates and 8 ballots', 413);
  if (method === 'maximal-lotteries' && candidates.length > 6) throw new ElectionError('Maximal lotteries supports at most 6 candidates', 413);
  return { method, candidates: [...candidates], ballots, maxScore, budget, seed, total };
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
function condorcet(active: string[], matrix: Pairwise): string[] {
  return active.filter(c => active.every(d => c === d || matrix[c][d] > matrix[d][c]));
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

export function countPlurality(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) tally[b.choice ?? b.ranking![0]] += b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally}]);
}
export function countAntiPlurality(ctx: Context): SimulationResult {
  const vetoes = zeros(ctx.candidates);
  for (const b of ctx.ballots) vetoes[b.choice ?? b.ranking!.at(-1)!] += b.count;
  return result(ctx, best(ctx.candidates, vetoes, true), [{vetoes}]);
}
export function countTwoRound(ctx: Context): SimulationResult {
  const tally = firstCounts(ctx, ctx.candidates);
  const trace: Trace = [{round: 1, tally}];
  const leaders = best(ctx.candidates, tally);
  if (tally[leaders[0]] * 2 > ctx.total || ctx.candidates.length === 1) return result(ctx, leaders, trace);
  const finalists = [...ctx.candidates].sort((a, b) => tally[b] - tally[a] || ctx.candidates.indexOf(a) - ctx.candidates.indexOf(b)).slice(0, 2);
  const runoff = firstCounts(ctx, finalists);
  trace.push({round: 2, active: finalists, tally: runoff});
  return result(ctx, best(finalists, runoff), trace);
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
export function countCoombs(ctx: Context): SimulationResult { return elimination(ctx, 'coombs'); }
export function countNanson(ctx: Context): SimulationResult { return elimination(ctx, 'nanson'); }
export function countBaldwin(ctx: Context): SimulationResult { return elimination(ctx, 'baldwin'); }
export function countTidemanAlternative(ctx: Context): SimulationResult { return elimination(ctx, 'tideman-alternative'); }
export function countMinimax(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const worstDefeat = zeros(ctx.candidates);
  for (const c of ctx.candidates) worstDefeat[c] = Math.max(0, ...ctx.candidates.filter(d => c !== d).map(d => matrix[d][c] - matrix[c][d]));
  return result(ctx, best(ctx.candidates, worstDefeat, true), [{pairwise: matrix}, {worstDefeat}]);
}
export function countCopeland(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const tally = zeros(ctx.candidates);
  for (const c of ctx.candidates) for (const d of ctx.candidates) if (c !== d) tally[c] += matrix[c][d] > matrix[d][c] ? 1 : matrix[c][d] === matrix[d][c] ? 0.5 : 0;
  return result(ctx, best(ctx.candidates, tally), [{pairwise: matrix}, {tally}]);
}
export function countBlack(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const winner = condorcet(ctx.candidates, matrix);
  if (winner.length) return result(ctx, winner, [{pairwise: matrix}, {condorcet: winner}]);
  const tally = bordaCounts(ctx, ctx.candidates);
  return result(ctx, best(ctx.candidates, tally), [{pairwise: matrix}, {fallback: 'borda'}, {tally}]);
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
function reachable(edges: Record<string, string[]>, from: string, target: string): boolean {
  const seen = new Set<string>();
  const stack = [from];
  while (stack.length) { const c = stack.pop()!; if (c === target) return true; if (!seen.has(c)) { seen.add(c); stack.push(...edges[c]); } }
  return false;
}
export function countRankedPairs(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const edges = Object.fromEntries(ctx.candidates.map(c => [c, [] as string[]]));
  const victories: [string, string][] = [];
  for (const c of ctx.candidates) for (const d of ctx.candidates) if (matrix[c][d] > matrix[d][c]) victories.push([c, d]);
  victories.sort(([a, b], [c, d]) => matrix[c][d] - matrix[a][b] || ctx.candidates.indexOf(a) - ctx.candidates.indexOf(c) || ctx.candidates.indexOf(b) - ctx.candidates.indexOf(d));
  const decisions: Record<string, unknown>[] = [];
  for (const [winner, loser] of victories) {
    const locked = !reachable(edges, loser, winner);
    if (locked) edges[winner].push(loser);
    decisions.push({from: winner, to: loser, strength: matrix[winner][loser], locked});
  }
  return result(ctx, ctx.candidates.filter(c => ctx.candidates.every(d => !edges[d].includes(c))), [{pairwise: matrix}, {edges: decisions}]);
}
export function countSchulze(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const paths = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const c of ctx.candidates) for (const d of ctx.candidates) if (matrix[c][d] > matrix[d][c]) paths[c][d] = matrix[c][d];
  for (const via of ctx.candidates) for (const from of ctx.candidates) if (from !== via) for (const to of ctx.candidates) if (to !== via && to !== from)
    paths[from][to] = Math.max(paths[from][to], Math.min(paths[from][via], paths[via][to]));
  return result(ctx, ctx.candidates.filter(c => ctx.candidates.every(d => c === d || paths[c][d] >= paths[d][c])), [{pairwise: matrix}, {strongestPaths: paths}]);
}
export function countBorda(ctx: Context): SimulationResult {
  const tally = bordaCounts(ctx, ctx.candidates);
  return result(ctx, best(ctx.candidates, tally), [{tally}]);
}
export function countBucklin(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  const trace: Trace = [];
  for (let depth = 1; depth <= ctx.candidates.length; depth++) {
    for (const b of ctx.ballots) tally[b.ranking![depth - 1]] += b.count;
    trace.push({depth, tally: {...tally}});
    if (Math.max(...Object.values(tally)) * 2 > ctx.total) break;
  }
  return result(ctx, best(ctx.candidates, tally), trace);
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
export function countApproval(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of b.approvals!) tally[c] += b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally}]);
}
export function countScore(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.scores![c] * b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally}]);
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
export function countStar(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.scores![c] * b.count;
  const finalists = [...ctx.candidates].sort((a, b) => tally[b] - tally[a] || ctx.candidates.indexOf(a) - ctx.candidates.indexOf(b)).slice(0, 2);
  const runoff = zeros(finalists);
  if (finalists.length === 2) for (const b of ctx.ballots) {
    const [a, c] = finalists;
    if (b.scores![a] > b.scores![c]) runoff[a] += b.count;
    if (b.scores![c] > b.scores![a]) runoff[c] += b.count;
  }
  return result(ctx, best(finalists, runoff), finalists.length === 1 ? [{stage: 'score', tally, finalists}] : [{stage: 'score', tally, finalists}, {stage: 'runoff', tally: runoff}]);
}
export function countQuadratic(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.credits![c] * b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally, budget: ctx.budget}]);
}
function randomUnit(seed: number): number { return ((Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296; }
function sample(probabilities: number[], seed: number): number {
  const draw = randomUnit(seed);
  let cumulative = 0;
  for (let i = 0; i < probabilities.length; i++) { cumulative += probabilities[i]; if (draw < cumulative) return i; }
  return probabilities.length - 1;
}
export function countRandomBallot(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) tally[b.choice ?? b.ranking![0]] += b.count;
  const probabilities = ctx.candidates.map(c => tally[c] / ctx.total);
  const chosen = sample(probabilities, ctx.seed);
  return result(ctx, [ctx.candidates[chosen]], [{tally, seed: ctx.seed}], probabilities);
}
export function countSortition(ctx: Context): SimulationResult {
  const probabilities = ctx.candidates.map(() => 1 / ctx.candidates.length);
  const chosen = sample(probabilities, ctx.seed);
  return result(ctx, [ctx.candidates[chosen]], [{seed: ctx.seed}], probabilities);
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

export function simulate(request: unknown): SimulationResult {
  const ctx = normalize(request);
  const counters: Record<Method, (c: Context) => SimulationResult> = {
    'plurality': countPlurality, 'anti-plurality': countAntiPlurality, 'two-round': countTwoRound,
    'instant-runoff': countInstantRunoff, 'coombs': countCoombs, 'nanson': countNanson,
    'baldwin': countBaldwin, 'tideman-alternative': countTidemanAlternative, 'minimax': countMinimax,
    'copeland': countCopeland, 'black': countBlack, 'kemeny-young': countKemenyYoung,
    'ranked-pairs': countRankedPairs, 'schulze': countSchulze, 'borda': countBorda,
    'bucklin': countBucklin, 'dodgson': countDodgson, 'approval': countApproval,
    'majority-judgment': countMajorityJudgment, 'score': countScore, 'star': countStar,
    'quadratic': countQuadratic, 'random-ballot': countRandomBallot,
    'maximal-lotteries': countMaximalLotteries, 'sortition': countSortition,
  };
  return counters[ctx.method](ctx);
}
