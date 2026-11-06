/** Ballot-family API. Counting and canonical validation stay in the engines. */
import { METHODS, ElectionError, simulate } from './electoral.ts';
import type { Method, ElectionRequest, SimulationResult } from './electoral.ts';
import { METHODS as MULTI_METHODS, ElectionError as MultiElectionError, simulate as simulateMulti } from './multi_winner.ts';
import type { Method as MultiMethod, ElectionRequest as MultiElectionRequest, SimulationResult as MultiSimulationResult } from './multi_winner.ts';

export type { ElectionRequest, SimulationResult, MultiElectionRequest, MultiSimulationResult };
export type BallotFamily = 'ranked' | 'marked' | 'approval' | 'scored' | 'quadratic' | 'none';
export type MultiBallotFamily = Exclude<BallotFamily, 'quadratic'> | 'cumulative';
const fields = {ranked: 'ranking', marked: 'choice', approval: 'approvals', scored: 'scores', quadratic: 'credits', cumulative: 'votes', none: null} as const;
const marked = ['plurality', 'anti-plurality', 'random-ballot'] as const;
const scored = ['score', 'star', 'majority-judgment'] as const;
const multiApproval = ['approval', 'proportional-approval', 'sequential-proportional-approval', 'phragmen', 'limited-vote'] as const;
export const FAMILY_METHODS: Readonly<Record<BallotFamily, readonly Method[]>> = Object.freeze({
  ranked: Object.freeze(METHODS.filter(m => !['approval', ...scored, 'quadratic', 'sortition'].includes(m))),
  marked: Object.freeze(marked), approval: Object.freeze(['approval'] as const),
  scored: Object.freeze(scored), quadratic: Object.freeze(['quadratic'] as const), none: Object.freeze(['sortition'] as const),
});
export const MULTI_FAMILY_METHODS: Readonly<Record<MultiBallotFamily, readonly MultiMethod[]>> = Object.freeze({
  ranked: Object.freeze(MULTI_METHODS.filter(m => ![...multiApproval, 'reweighted-range', 'cumulative', 'sortition'].includes(m))),
  marked: Object.freeze(['single-non-transferable'] as const), approval: Object.freeze(multiApproval),
  scored: Object.freeze(['reweighted-range'] as const), cumulative: Object.freeze(['cumulative'] as const), none: Object.freeze(['sortition'] as const),
});

type BallotFormats = {
  ranked: {ranking: string[]; count?: number}; marked: {choice: string; count?: number};
  approval: {approvals: string[]; count?: number}; scored: {scores: Record<string, number>; count?: number};
  quadratic: {credits: Record<string, number>; count?: number}; cumulative: {votes: Record<string, number>; count?: number};
  none: never;
};
type FamilyMethod = {
  ranked: Exclude<Method, 'approval' | typeof scored[number] | 'quadratic' | 'sortition'>;
  marked: typeof marked[number]; approval: 'approval'; scored: typeof scored[number];
  quadratic: 'quadratic'; none: 'sortition';
};
type MultiFamilyMethod = {
  ranked: Exclude<MultiMethod, typeof multiApproval[number] | 'reweighted-range' | 'cumulative' | 'sortition'>;
  marked: 'single-non-transferable'; approval: typeof multiApproval[number];
  scored: 'reweighted-range'; cumulative: 'cumulative'; none: 'sortition';
};
// Engines accept the same option object for every method. Do not invent narrower
// option rules here; dynamic bounds (such as limited-vote) remain engine checks.
export type FamilyRequest<F extends BallotFamily> = Omit<ElectionRequest, 'method' | 'ballots'> & {method: FamilyMethod[F]; ballots: BallotFormats[F][]};
export type MultiFamilyRequest<F extends MultiBallotFamily> = Omit<MultiElectionRequest, 'method' | 'ballots'> & {method: MultiFamilyMethod[F]; ballots: BallotFormats[F][]};

function object(input: unknown): input is Record<string, unknown> {
  return input !== null && typeof input === 'object' && !Array.isArray(input);
}
function inferFamily(input: unknown, catalogs: Readonly<Record<string, readonly string[]>>): string | undefined {
    if (object(input) && Array.isArray(input.ballots)) {
      if (!input.ballots.length && input.method === 'sortition') return 'none';
      else if (input.ballots.every(object)) {
        const formats = new Set(input.ballots.flatMap(b => Object.values(fields).filter(f => f !== null && Object.hasOwn(b, f))));
        if (formats.size === 1) return Object.keys(catalogs).find(f => fields[f as keyof typeof fields] === [...formats][0]);
      }
    }
    return undefined;
}
function dispatch<R>(input: unknown, family: string, catalogs: Readonly<Record<string, readonly string[]>>,
  engine: (input: unknown) => R, ErrorType: typeof ElectionError): R {
  if (!Object.hasOwn(catalogs, family)) throw new ErrorType('Unknown ballot family');
  if (!object(input)) throw new ErrorType('Request must be an object');
  if (!catalogs[family].includes(input.method as string)) throw new ErrorType(`Method is not compatible with ${family} ballots`);
  const field = fields[family as keyof typeof fields];
  if (Array.isArray(input.ballots)) for (const ballot of input.ballots) {
    if (!object(ballot) || field === null || !Object.hasOwn(ballot, field) ||
        Object.values(fields).some(f => f !== null && f !== field && Object.hasOwn(ballot, f)))
      throw new ErrorType(`Expected only ${family} ballots`);
  }
  return engine(input);
}

export function simulateRequest(input: unknown, family?: BallotFamily): SimulationResult {
  const selected = family === undefined ? inferFamily(input, FAMILY_METHODS) : family;
  switch (selected) {
    case 'ranked': return simulateRanked(input);
    case 'marked': return simulateMarked(input);
    case 'approval': return simulateApproval(input);
    case 'scored': return simulateScored(input);
    case 'quadratic': return simulateQuadratic(input);
    case 'none': return simulateNone(input);
    case undefined: return simulate(input); // Preserve legacy mixed formats.
    default: throw new ElectionError('Unknown ballot family');
  }
}
export function simulateMultiRequest(input: unknown, family?: MultiBallotFamily): MultiSimulationResult {
  const selected = family === undefined ? inferFamily(input, MULTI_FAMILY_METHODS) : family;
  switch (selected) {
    case 'ranked': return simulateMultiRanked(input);
    case 'marked': return simulateMultiMarked(input);
    case 'approval': return simulateMultiApproval(input);
    case 'scored': return simulateMultiScored(input);
    case 'cumulative': return simulateMultiCumulative(input);
    case 'none': return simulateMultiNone(input);
    case undefined: return simulateMulti(input);
    default: throw new MultiElectionError('Unknown ballot family');
  }
}

// Accept unknown at every public boundary so parsed JSON is always validated.
export function simulateRanked(input: unknown): SimulationResult {return dispatch(input, 'ranked', FAMILY_METHODS, simulate, ElectionError);}
export function simulateMarked(input: unknown): SimulationResult {return dispatch(input, 'marked', FAMILY_METHODS, simulate, ElectionError);}
export function simulateApproval(input: unknown): SimulationResult {return dispatch(input, 'approval', FAMILY_METHODS, simulate, ElectionError);}
export function simulateScored(input: unknown): SimulationResult {return dispatch(input, 'scored', FAMILY_METHODS, simulate, ElectionError);}
export function simulateQuadratic(input: unknown): SimulationResult {return dispatch(input, 'quadratic', FAMILY_METHODS, simulate, ElectionError);}
export function simulateNone(input: unknown): SimulationResult {return dispatch(input, 'none', FAMILY_METHODS, simulate, ElectionError);}
export function simulateMultiRanked(input: unknown): MultiSimulationResult {return dispatch(input, 'ranked', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
export function simulateMultiMarked(input: unknown): MultiSimulationResult {return dispatch(input, 'marked', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
export function simulateMultiApproval(input: unknown): MultiSimulationResult {return dispatch(input, 'approval', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
export function simulateMultiScored(input: unknown): MultiSimulationResult {return dispatch(input, 'scored', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
export function simulateMultiCumulative(input: unknown): MultiSimulationResult {return dispatch(input, 'cumulative', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
export function simulateMultiNone(input: unknown): MultiSimulationResult {return dispatch(input, 'none', MULTI_FAMILY_METHODS, simulateMulti, MultiElectionError);}
