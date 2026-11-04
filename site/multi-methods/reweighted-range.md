# Reweighted range voting

Elect a high-scoring candidate, then reduce the influence of ballots that gave strong scores to candidates already elected.

**Ballot:** scores. **API identifier:** `reweighted-range` at `/multi/simulate`.

## Counting rule

1. Give each ballot initial weight 1.
2. For each unelected candidate, sum count × weight × score; elect the largest total.
3. Recompute each ballot’s weight as maxScore/(maxScore + the sum of its scores for elected candidates), and repeat.

**Implemented variant:** RRV with C=1 in normalized 0–1 scores. The API accepts explicit integer scores from 0 to maxScore; arithmetic comparisons are exact.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "reweighted-range",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "ballots": [
    {
      "scores": {
        "A": 5,
        "B": 4,
        "C": 0,
        "D": 0
      },
      "count": 6
    },
    {
      "scores": {
        "A": 0,
        "B": 0,
        "C": 5,
        "D": 4
      },
      "count": 3
    },
    {
      "scores": {
        "A": 0,
        "B": 0,
        "C": 4,
        "D": 5
      },
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

**The selected committee is A and C.** Initial score totals are A 30, B 24, C 19, D 17. A wins the first seat. Its six supporters then have half weight: B falls to 12 while C retains 19. The second seat goes to C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "reweighted-range",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "round": 1,
      "weights": [
        1.0,
        1.0,
        1.0
      ],
      "tally": {
        "A": 30.0,
        "B": 24.0,
        "C": 19.0,
        "D": 17.0
      },
      "selected": "A",
      "tied": [
        "A"
      ]
    },
    {
      "round": 2,
      "weights": [
        0.5,
        1.0,
        1.0
      ],
      "tally": {
        "B": 12.0,
        "C": 19.0,
        "D": 17.0
      },
      "selected": "C",
      "tied": [
        "C"
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Reweighted range voting — complete algorithm">

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

def count_reweighted_range(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        weights = [Fraction(options["maxScore"], options["maxScore"]+sum(b["scores"][x] for x in elected)) for b in ballots]
        tally = {x: sum((b["count"]*weight*b["scores"][x] for b, weight in zip(ballots, weights)), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "weights": [float(w) for w in weights], "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'reweighted-range', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'scores': {'A': 5, 'B': 4, 'C': 0, 'D': 0}, 'count': 6}, {'scores': {'A': 0, 'B': 0, 'C': 5, 'D': 4}, 'count': 3}, {'scores': {'A': 0, 'B': 0, 'C': 4, 'D': 5}, 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_reweighted_range(election["candidates"], election["ballots"], election["seats"], election["options"])
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

export function countReweightedRange(ctx: Context): SimulationResult {return sequential(ctx, 'reweighted-range');}

const election: Context = {
  "method": "reweighted-range",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "scores": {
        "A": 5,
        "B": 4,
        "C": 0,
        "D": 0
      },
      "count": 6
    },
    {
      "scores": {
        "A": 0,
        "B": 0,
        "C": 5,
        "D": 4
      },
      "count": 3
    },
    {
      "scores": {
        "A": 0,
        "B": 0,
        "C": 4,
        "D": 5
      },
      "count": 1
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "limit": 1,
  "seed": 1,
  "total": 10
};
console.log(JSON.stringify(countReweightedRange(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/reweighted-range.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/reweighted-range.ts) program.

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
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | pass | Increasing one elected candidate’s own support cannot worsen its compared score relative to opponents. In the reweighted sequential rule it can move the candidate to an earlier election round; it does not require retaining the same other winners. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | pass | Each round is independent of the final target size. With fixed options and tie priority, a larger committee continues the same selection sequence instead of replacing earlier members. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | conditional | For this chosen-set removal test, deleting a never-selected candidate leaves every round on the unchanged selected path and does not change represented counts or loads. This argument is specific to fixed submitted ballots and the implemented sequential tie order, not a full social-ranking IIA theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
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
| [Summability](/multi-criteria.md#summability) | pass | A histogram of complete score vectors suffices. With g=maxScore+1 grades, this may need O(g^m) entries; candidate totals alone lose the score correlations needed for reweighting. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(kbm) tally work with incremental elected-score totals.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Smith: Reweighted Range Voting (2005)](https://rangevoting.org/WarrenSmithPages/homepage/rerange.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
