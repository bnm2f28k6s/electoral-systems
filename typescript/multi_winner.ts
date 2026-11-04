/** Multi-winner teaching algorithms; no imports or runtime dependencies. */
// BEGIN shared
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
// END shared

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function integer(value: unknown, low: number, high: number, name: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < low || value > high)
    throw new ElectionError(`${name} must be an integer from ${low} to ${high}`);
  return value;
}
function exactKeys(value: Record<string, unknown>, allowed: string[], name: string): void {
  if (Object.keys(value).some(key => !allowed.includes(key))) throw new ElectionError(`Unknown field in ${name}`);
}
export function normalize(input: unknown): Context {
  if (!object(input)) throw new ElectionError('Request must be an object');
  exactKeys(input, ['method', 'candidates', 'seats', 'ballots', 'options'], 'request');
  if (!(METHODS as readonly unknown[]).includes(input.method)) throw new ElectionError('Unknown multi-winner method');
  const method = input.method as Method;
  const candidates = input.candidates;
  if (!Array.isArray(candidates) || !candidates.length || candidates.some(c => typeof c !== 'string' || /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u.test(c) || Array.from(c).length > 100) || new Set(candidates).size !== candidates.length)
    throw new ElectionError('candidates must be unique nonempty strings of at most 100 characters');
  if (candidates.length > 32) throw new ElectionError('At most 32 candidates are supported', 413);
  const seats = integer(input.seats, 1, candidates.length, 'seats');
  const opts = Object.hasOwn(input, 'options') ? input.options : {};
  if (!object(opts)) throw new ElectionError('options must be an object');
  exactKeys(opts, ['maxScore', 'budget', 'limit', 'seed'], 'options');
  const maxScore = integer(Object.hasOwn(opts, 'maxScore') ? opts.maxScore : 5, 1, 100, 'maxScore');
  const budget = integer(Object.hasOwn(opts, 'budget') ? opts.budget : 100, 1, 1000000, 'budget');
  const limit = integer(Object.hasOwn(opts, 'limit') ? opts.limit : Math.max(1, seats - 1), 1, 32, 'limit');
  if (method === 'limited-vote' && !((seats === 1 && limit === 1) || limit < seats)) throw new ElectionError('limit must be smaller than seats');
  const seed = integer(Object.hasOwn(opts, 'seed') ? opts.seed : 1, 0, 4294967295, 'seed');
  if (!Array.isArray(input.ballots)) throw new ElectionError('ballots must be an array');
  if (input.ballots.length > 10000) throw new ElectionError('At most 10000 ballot groups are supported', 413);
  let total = 0;
  const ballots = input.ballots.map((b: unknown) => {
    if (!object(b)) throw new ElectionError('Each ballot must be an object');
    exactKeys(b, ['ranking', 'approvals', 'choice', 'scores', 'votes', 'count'], 'ballot');
    const count = integer(Object.hasOwn(b, 'count') ? b.count : 1, 1, 1000000, 'count');
    total += count;
    const formats = ['ranking', 'approvals', 'choice', 'scores', 'votes'].filter(field => Object.hasOwn(b, field));
    if (formats.length !== 1) throw new ElectionError('Each ballot needs exactly one format');
    const field = formats[0];
    const expected = ['approval', 'proportional-approval', 'sequential-proportional-approval', 'phragmen', 'limited-vote'].includes(method) ? 'approvals' : method === 'reweighted-range' ? 'scores' : method === 'cumulative' ? 'votes' : 'ranking';
    if (!(method === 'single-non-transferable' ? ['choice', 'ranking'].includes(field) : field === expected)) throw new ElectionError('Wrong ballot format for ' + method);
    if (field === 'ranking') {
      if (!Array.isArray(b.ranking) || b.ranking.length !== candidates.length || new Set(b.ranking).size !== candidates.length || b.ranking.some(c => !candidates.includes(c))) throw new ElectionError('ranking must list every candidate exactly once');
    } else if (field === 'approvals') {
      if (!Array.isArray(b.approvals) || new Set(b.approvals).size !== b.approvals.length || b.approvals.some(c => !candidates.includes(c))) throw new ElectionError('approvals must be a subset without duplicates');
      if (method === 'limited-vote' && b.approvals.length > limit) throw new ElectionError('Too many limited-vote marks');
    } else if (field === 'choice') {
      if (!candidates.includes(b.choice)) throw new ElectionError('choice must name a candidate');
    } else {
      const values = b[field];
      if (!object(values) || Object.keys(values).length !== candidates.length || candidates.some(c => !Object.hasOwn(values, c))) throw new ElectionError(`${field} must contain every candidate exactly once`);
      for (const c of candidates) integer(values[c], 0, field === 'scores' ? maxScore : budget, field);
      if (field === 'votes' && Object.values(values).reduce((sum: number, value: any) => sum + value, 0) > budget) throw new ElectionError('Cumulative ballot exceeds its budget');
    }
    return {...b, count} as Ballot & {count: number};
  });
  if (total > 1000000) throw new ElectionError('At most 1000000 represented voters', 413);
  if (method === 'sortition') {if (ballots.length) throw new ElectionError('Sortition accepts no ballots');}
  else if (!ballots.length) throw new ElectionError('At least one ballot is required');
  if (['proportional-approval', 'minimax-external-opposition'].includes(method) && candidates.length > 8) throw new ElectionError('Exact committee enumeration supports at most 8 candidates', 413);
  if (['cpo-stv', 'schulze-stv'].includes(method) && (candidates.length > 6 || ballots.length > 100)) throw new ElectionError('Exact STV comparisons support at most 6 candidates and 100 ballot groups', 413);
  return {method, candidates: [...candidates], seats, ballots, maxScore, budget, limit, seed, total};
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
function zeros(candidates: string[]): Tally {return Object.fromEntries(candidates.map(c => [c, 0]));}
function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function selectTop(candidates: string[], tally: Tally, seats: number): {winners: string[]; tie: boolean} {
  const sorted = [...candidates].sort((a, b) => tally[b] - tally[a]);
  const selected = sorted.slice(0, seats);
  return {winners: candidates.filter(c => selected.includes(c)),
    tie: seats < candidates.length && tally[sorted[seats - 1]] === tally[sorted[seats]]};
}
function pairwise(ctx: Context): Matrix {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const ballot of ctx.ballots) {
    const ranking = ballot.ranking!;
    ranking.forEach((a, index) => {for (const b of ranking.slice(index + 1)) matrix[a][b] += ballot.count;});
  }
  return matrix;
}
function bordaCounts(ctx: Context): Tally {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) ballot.ranking!.forEach((c, index) => {tally[c] += (ctx.candidates.length - 1 - index) * ballot.count;});
  return tally;
}
export function countApproval(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) for (const c of ballot.approvals!) tally[c] += ballot.count;
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}
export function countKBorda(ctx: Context): SimulationResult {
  const tally = bordaCounts(ctx);
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}
export function countBloc(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) for (const c of ballot.ranking!.slice(0, ctx.seats)) tally[c] += ballot.count;
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}
export function countSingleNonTransferable(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) tally[ballot.choice ?? ballot.ranking![0]] += ballot.count;
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}
export function countLimitedVote(ctx: Context): SimulationResult {
  return countApproval(ctx);
}
export function countCumulative(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) for (const c of ctx.candidates) tally[c] += ballot.votes![c] * ballot.count;
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}
export function countMinimax(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const tally = Object.fromEntries(ctx.candidates.map(c => [c, ctx.candidates.length > 1 ? Math.min(...ctx.candidates.filter(x => x !== c).map(x => matrix[c][x])) : ctx.total]));
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{pairwise: matrix}, {simpsonScores: tally}]);
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
export function countProportionalApproval(ctx: Context): SimulationResult {
  return optimize(ctx, committee => {
    let score = fraction(0);
    for (const ballot of ctx.ballots) {
      const approved = committee.filter(c => ballot.approvals!.includes(c)).length;
      for (let j = 1; j <= approved; j++) score = add(score, fraction(ballot.count, j));
    }
    return score;
  });
}
export function countMinimaxExternalOpposition(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  return optimize(ctx, committee => {
    const outside = ctx.candidates.filter(c => !committee.includes(c));
    const minimum = outside.length ? Math.min(...committee.flatMap(a => outside.map(b => matrix[a][b]))) : ctx.total;
    return fraction(minimum);
  }, [{pairwise: matrix}]);
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
export function countReweightedRange(ctx: Context): SimulationResult {return sequential(ctx, 'reweighted-range');}

export function countPhragmen(ctx: Context): SimulationResult {
  let loads = ctx.ballots.map(() => fraction(0));
  const elected: string[] = [], trace: Trace = [];
  let tie = false;
  for (let step = 0; step < ctx.seats; step++) {
    const candidates = ctx.candidates.filter(c => !elected.includes(c));
    const levels: Record<string, Fraction | null> = Object.fromEntries(candidates.map(c => {
      const support = ctx.ballots.reduce((sum, b) => sum + (b.approvals!.includes(c) ? b.count : 0), 0);
      let load = fraction(1);
      ctx.ballots.forEach((b, i) => {if (b.approvals!.includes(c)) load = add(load, multiply(loads[i], fraction(b.count)));});
      return [c, support ? divide(load, fraction(support)) : null];
    }));
    let low: Fraction | null = null;
    for (const c of candidates) if (levels[c] !== null && (low === null || compare(levels[c]!, low) < 0)) low = levels[c];
    const tied = candidates.filter(c => low === null ? levels[c] === null : levels[c] !== null && compare(levels[c]!, low!) === 0);
    const selected = tied[0]; elected.push(selected); tie ||= tied.length > 1;
    if (low !== null) loads = ctx.ballots.map((b, i) => b.approvals!.includes(selected) ? low! : loads[i]);
    trace.push({round: step + 1, loadLevels: Object.fromEntries(candidates.map(c => [c, levels[c] === null ? null : asNumber(levels[c]!)])), selected, tied, loads: loads.map(asNumber)});
  }
  return result(ctx, elected, tie, trace);
}
function droopFraction(total: number, seats: number): Fraction {
  return add(fraction(total, seats + 1), fraction(1, (seats + 1) ** 2));
}
export function countExpandingApprovals(ctx: Context): SimulationResult {
  const quota = droopFraction(ctx.total, ctx.seats);
  const rankVectors = Object.fromEntries(ctx.candidates.map(c => [c, ctx.candidates.map((_, depth) => ctx.ballots.reduce((sum, b) => sum + (b.ranking![depth] === c ? b.count : 0), 0))]));
  const priority = [...ctx.candidates].sort((a, b) => {
    for (let depth = 0; depth < ctx.candidates.length; depth++) if (rankVectors[a][depth] !== rankVectors[b][depth]) return rankVectors[b][depth] - rankVectors[a][depth];
    return 0;
  });
  let weights = ctx.ballots.map(b => fraction(b.count));
  const elected: string[] = [];
  let depth = 1, tie = false;
  const trace: Trace = [{quota: asNumber(quota), priority, rankVectors}];
  while (elected.length < ctx.seats) {
    const candidates = ctx.candidates.filter(c => !elected.includes(c));
    const tally = Object.fromEntries(candidates.map(c => {
      let score = fraction(0);
      ctx.ballots.forEach((b, i) => {if (b.ranking!.slice(0, depth).includes(c)) score = add(score, weights[i]);});
      return [c, score];
    }));
    const eligible = priority.filter(c => Object.hasOwn(tally, c) && compare(tally[c], quota) >= 0);
    const numeric = Object.fromEntries(candidates.map(c => [c, asNumber(tally[c])]));
    if (!eligible.length) {trace.push({depth, tally: numeric, eligible: []}); depth++; continue;}
    const selected = eligible[0];
    const tied = eligible.filter(c => rankVectors[c].every((value, i) => value === rankVectors[selected][i]));
    tie ||= tied.length > 1; elected.push(selected);
    const factor = divide(subtract(tally[selected], quota), tally[selected]);
    weights = ctx.ballots.map((b, i) => b.ranking!.slice(0, depth).includes(selected) ? multiply(weights[i], factor) : weights[i]);
    trace.push({depth, tally: numeric, eligible, selected, tied, remainingWeights: weights.map(asNumber)});
  }
  return result(ctx, elected, tie, trace);
}
export function countQuotaBorda(ctx: Context): SimulationResult {
  const quota = droopFraction(ctx.total, ctx.seats), borda = bordaCounts(ctx);
  const elected: string[] = [], trace: Trace = [{quota: asNumber(quota), borda}];
  let tie = false;
  for (let depth = 1; depth <= ctx.candidates.length; depth++) {
    const groups = new Map<string, {candidates: string[]; count: number}>();
    for (const b of ctx.ballots) {
      const prefix = ctx.candidates.filter(c => b.ranking!.slice(0, depth).includes(c));
      const key = JSON.stringify(prefix), old = groups.get(key);
      if (old) old.count += b.count; else groups.set(key, {candidates: prefix, count: b.count});
    }
    while (elected.length < ctx.seats) {
      const unmet = [...groups.values()].map(g => ({candidates: g.candidates,
        seats: Math.min(g.candidates.length, Number(BigInt(g.count) * quota[1] / quota[0]))})).filter(g => g.candidates.filter(c => elected.includes(c)).length < g.seats);
      if (!unmet.length) break;
      const eligible = ctx.candidates.filter(c => !elected.includes(c) && unmet.some(g => g.candidates.includes(c)));
      const high = Math.max(...eligible.map(c => borda[c]));
      const tied = eligible.filter(c => borda[c] === high), selected = tied[0];
      elected.push(selected); tie ||= tied.length > 1;
      trace.push({depth, demands: unmet, selected, tied});
    }
  }
  return result(ctx, elected, tie, trace);
}
export function countStv(ctx: Context): SimulationResult {
  const quota = Math.floor(ctx.total / (ctx.seats + 1)) + 1;
  let weights = ctx.ballots.map(b => fraction(b.count));
  const active = [...ctx.candidates], elected: string[] = [], trace: Trace = [{quota}];
  let tie = false;
  while (elected.length < ctx.seats) {
    if (active.length === ctx.seats - elected.length) {elected.push(...active); trace.push({electedRemaining: [...active]}); break;}
    const choices = ctx.ballots.map(b => b.ranking!.find(c => active.includes(c))!);
    const tally = Object.fromEntries(active.map(c => {
      let score = fraction(0); choices.forEach((choice, i) => {if (choice === c) score = add(score, weights[i]);}); return [c, score];
    }));
    const numeric = Object.fromEntries(active.map(c => [c, asNumber(tally[c])]));
    const eligible = active.filter(c => compare(tally[c], fraction(quota)) >= 0);
    if (eligible.length) {
      let high = tally[eligible[0]];
      for (const c of eligible) if (compare(tally[c], high) > 0) high = tally[c];
      const tied = eligible.filter(c => compare(tally[c], high) === 0), winner = tied[0]; tie ||= tied.length > 1;
      const factor = divide(subtract(tally[winner], fraction(quota)), tally[winner]);
      weights = weights.map((w, i) => choices[i] === winner ? multiply(w, factor) : w);
      elected.push(winner); active.splice(active.indexOf(winner), 1);
      trace.push({tally: numeric, elected: winner, tied, transferFactor: asNumber(factor)});
    } else {
      let low = tally[active[0]];
      for (const c of active) if (compare(tally[c], low) < 0) low = tally[c];
      const tied = active.filter(c => compare(tally[c], low) === 0), loser = tied[tied.length - 1]; tie ||= tied.length > 1;
      active.splice(active.indexOf(loser), 1);
      trace.push({tally: numeric, eliminated: loser, tied});
    }
  }
  return result(ctx, elected, tie, trace);
}
function draw(candidates: string[], tally: Tally, seed: number): {winner: string; state: number; probabilities: Tally} {
  const state = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  const total = candidates.reduce((sum, c) => sum + tally[c], 0);
  const threshold = fraction(state, 4294967296);
  let cumulative = fraction(0), winner = candidates[candidates.length - 1], chosen = false;
  const probabilities = Object.fromEntries(candidates.map(c => [c, tally[c] / total]));
  for (const c of candidates) {
    cumulative = add(cumulative, fraction(tally[c], total));
    if (!chosen && compare(threshold, cumulative) < 0) {winner = c; chosen = true;}
  }
  return {winner, state, probabilities};
}
export function countSortition(ctx: Context): SimulationResult {
  const active = [...ctx.candidates], elected: string[] = [], trace: Trace = [];
  let seed = ctx.seed;
  for (let step = 0; step < ctx.seats; step++) {
    const {winner, state, probabilities} = draw(active, Object.fromEntries(active.map(c => [c, 1])), seed);
    seed = state; elected.push(winner); active.splice(active.indexOf(winner), 1);
    trace.push({round: step + 1, probabilities, selected: winner, state});
  }
  return result(ctx, elected, false, trace);
}
export function countMultipleRandomBallots(ctx: Context): SimulationResult {
  const active = [...ctx.candidates], elected: string[] = [], trace: Trace = [];
  let seed = ctx.seed;
  for (let step = 0; step < ctx.seats; step++) {
    const tally = zeros(active);
    for (const b of ctx.ballots) tally[b.ranking!.find(c => active.includes(c))!] += b.count;
    const {winner, state, probabilities} = draw(active, tally, seed);
    seed = state; elected.push(winner); active.splice(active.indexOf(winner), 1);
    trace.push({round: step + 1, tally, probabilities, selected: winner, state});
  }
  return result(ctx, elected, false, trace);
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
export function simulate(request: unknown): SimulationResult {
  const ctx = normalize(request);
  const counters: Record<Method, (ctx: Context) => SimulationResult> = {
    'approval': countApproval, 'proportional-approval': countProportionalApproval,
    'sequential-proportional-approval': countSequentialProportionalApproval,
    'reweighted-range': countReweightedRange, 'stv': countStv, 'cpo-stv': countCpoStv,
    'schulze-stv': countSchulzeStv, 'phragmen': countPhragmen, 'k-borda': countKBorda,
    'bloc': countBloc, 'quota-borda': countQuotaBorda, 'expanding-approvals': countExpandingApprovals,
    'minimax': countMinimax, 'minimax-external-opposition': countMinimaxExternalOpposition,
    'single-non-transferable': countSingleNonTransferable, 'limited-vote': countLimitedVote,
    'cumulative': countCumulative, 'sortition': countSortition, 'multiple-random-ballots': countMultipleRandomBallots,
  };
  return counters[ctx.method](ctx);
}
