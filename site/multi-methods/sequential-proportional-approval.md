# Sequential proportional approval voting

Fill seats one at a time. An approval from a voter already represented by t elected candidates counts as 1/(t+1).

**Ballot:** approvals. **API identifier:** `sequential-proportional-approval` at `/multi/simulate`.

## Counting rule

1. Start with an empty committee.
2. For each unelected candidate, add count/(1+t) from each approving ballot, where t is that ballot’s already elected approved candidates.
3. Elect a candidate of greatest weighted support and repeat until k seats are filled.

**Implemented variant:** Forward sequential PAV (seq-PAV), using harmonic marginal gains. It need not find the globally optimal PAV committee.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "sequential-proportional-approval",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
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
  "options": {
    "maxScore": 5,
    "budget": 100,
    "limit": 1,
    "seed": 1
  }
}
```

**The selected committee is A and D.** A and B initially tie with six approvals. Priority selects A. Those six voters then contribute only half a point to B, giving B three points. D still has four, so D takes the second seat.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "sequential-proportional-approval",
  "seats": 2,
  "winners": [
    "A",
    "D"
  ],
  "tie": true,
  "trace": [
    {
      "round": 1,
      "tally": {
        "A": 6.0,
        "B": 6.0,
        "C": 3.0,
        "D": 4.0
      },
      "selected": "A",
      "tied": [
        "A",
        "B"
      ]
    },
    {
      "round": 2,
      "tally": {
        "B": 3.0,
        "C": 3.0,
        "D": 4.0
      },
      "selected": "D",
      "tied": [
        "D"
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Sequential proportional approval voting — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def number_map(tally):
    return {x: float(value) if isinstance(value, Fraction) else value for x, value in tally.items()}

def count_sequential_proportional_approval(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        tally = {x: sum((Fraction(b["count"], 1+sum(y in b["approvals"] for y in elected)) for b in ballots if x in b["approvals"]), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'sequential-proportional-approval', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'approvals': ['A', 'B'], 'count': 6}, {'approvals': ['C', 'D'], 'count': 3}, {'approvals': ['D'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_sequential_proportional_approval(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
```

```typescript
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
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/sequential-proportional-approval.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/sequential-proportional-approval.ts) program.

## Simulate this committee through HTTP

Start `python3 python/server.py` from the repository root. Save the request above as `committee.json`, then run:

```sh
curl --fail-with-body http://127.0.0.1:8000/multi/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @committee.json
```

The server executes this Python counting function and returns the response shown above. The [committee API guide](/multi-api.md) explains the response fields and errors. The [single-winner endpoint](/api-design.md) remains available separately.

## Criteria and assumptions

Read the [multi-winner criteria guide](/multi-criteria.md) before comparing labels. A criterion concerns whole classes of elections, not just this worked count. **Conditional** requires the stated domain or tie assumptions. **Unverified** records an unresolved assessment for the exact variant, rather than filling an empty source cell with a guarantee. Several committee criteria depend on how a voter compares groups of candidates; those assumptions are part of the definition.

| Criterion | Assessment | Explanation and source |
| --- | --- | --- |
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | pass | The existing-ballot single-candidate approval monotonicity property is established for AV, PAV, seq-PAV and sequential Phragmén. This does not imply their stronger group-support property. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | fail | These rules satisfy single-candidate monotonicity but can lose a member of a jointly supported elected group after an existing ballot expands its approvals. The book distinguishes and documents the two properties. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | fail | Under the approval-count extension, published examples show these sequential rules can select a dominated committee; even the weaker closure-under-dominance property fails. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | fail | Under the approval-count extension, published examples show these sequential rules can select a dominated committee; even the weaker closure-under-dominance property fails. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | pass | Each round is independent of the final target size. With fixed options and tie priority, a larger committee continues the same selection sequence instead of replacing earlier members. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | conditional | For this chosen-set removal test, deleting a never-selected candidate leaves every round on the unchanged selected path and does not change represented counts or loads. This argument is specific to fixed submitted ballots and the implemented sequential tie order, not a full social-ranking IIA theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | fail | Choosing a sequence using the combined electorate can change the early reweighting or load decisions, even when the separate electorates agree on a final committee. The approval-based rule fails consistency. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | fail | Adding a universally supported candidate changes every ballot’s harmonic or score-reweighting baseline. The relative allocation of the other seats can change, unlike simply adding a reserved seat. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of all approval subsets can be added across precincts and preserves the exact profile. Its worst-case size is O(2^m), which is much larger than independent candidate totals. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | fail | Sequential PAV can fail even JR on sufficiently large committees; therefore it does not satisfy the general PJR or EJR guarantee either. Good small examples are not a universal proportionality proof. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | fail | Sequential PAV can fail even JR on sufficiently large committees; therefore it does not satisfy the general PJR or EJR guarantee either. Good small examples are not a universal proportionality proof. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | fail | Sequential PAV can fail even JR on sufficiently large committees; therefore it does not satisfy the general PJR or EJR guarantee either. Good small examples are not a universal proportionality proof. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(kbm) if each ballot’s represented count is updated after each selection.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Lackner and Skowron: sequential Thiele methods](https://arxiv.org/abs/2007.01795)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
