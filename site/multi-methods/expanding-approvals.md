# Expanding approvals rule (EAR)

Temporarily approve short ranking prefixes. Elect sufficiently supported candidates, spend part of their supporters’ weight, and expand the prefix when more support is needed.

**Ballot:** ranking. **API identifier:** `expanding-approvals` at `/multi/simulate`.

## Counting rule

1. Start with one unit of weight per voter and approve only the first ranked candidate.
2. If an unelected candidate’s current approved weight reaches quota q, elect the eligible candidate highest in the fixed rank-maximal priority; then proportionally reduce approving ballots’ weight by a total q.
3. When no unelected candidate reaches q, expand approvals to the next ranking position. Continue until k seats are filled.

**Implemented variant:** Strict-ranking EAR using q=N/(k+1)+1/(k+1)² and proportional reweighting. Its fixed priority is rank-maximal: compare each candidate’s original first-place count, then second-place count, and so on; input order breaks equal rank vectors. Equal ranks and the original generalized weak-order input are outside this API variant.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "expanding-approvals",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C",
        "D"
      ],
      "count": 6
    },
    {
      "ranking": [
        "C",
        "D",
        "A",
        "B"
      ],
      "count": 3
    },
    {
      "ranking": [
        "D",
        "C",
        "B",
        "A"
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

**The selected committee is A and C.** The exact quota is 31/9. A qualifies at depth one. Spending that quota leaves A's supporters with total weight 23/9. At depth two the C–D group still has weight four and qualifies; the rank-based priority chooses C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "expanding-approvals",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "quota": 3.4444444444444446,
      "priority": [
        "A",
        "C",
        "D",
        "B"
      ],
      "rankVectors": {
        "A": [
          6,
          0,
          3,
          1
        ],
        "B": [
          0,
          6,
          1,
          3
        ],
        "C": [
          3,
          1,
          6,
          0
        ],
        "D": [
          1,
          3,
          0,
          6
        ]
      }
    },
    {
      "depth": 1,
      "tally": {
        "A": 6.0,
        "B": 0.0,
        "C": 3.0,
        "D": 1.0
      },
      "eligible": [
        "A"
      ],
      "selected": "A",
      "tied": [
        "A"
      ],
      "remainingWeights": [
        2.5555555555555554,
        3.0,
        1.0
      ]
    },
    {
      "depth": 1,
      "tally": {
        "B": 0.0,
        "C": 3.0,
        "D": 1.0
      },
      "eligible": []
    },
    {
      "depth": 2,
      "tally": {
        "B": 2.5555555555555554,
        "C": 4.0,
        "D": 4.0
      },
      "eligible": [
        "C",
        "D"
      ],
      "selected": "C",
      "tied": [
        "C"
      ],
      "remainingWeights": [
        2.5555555555555554,
        0.4166666666666667,
        0.1388888888888889
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Expanding approvals rule (EAR) — complete algorithm">

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

def droop_fraction(total, seats):
    return Fraction(total, seats+1) + Fraction(1, (seats+1)**2)

def count_expanding_approvals(c, ballots, seats, options):
    quota = droop_fraction(sum(b["count"] for b in ballots), seats)
    rank_vectors = {x: tuple(sum(b["count"] for b in ballots if b["ranking"][depth] == x) for depth in range(len(c))) for x in c}
    priority = sorted(c, key=lambda x: tuple(-n for n in rank_vectors[x]))
    weights = [Fraction(b["count"]) for b in ballots]
    elected, depth, tie = [], 1, False
    trace = [{"quota": float(quota), "priority": priority, "rankVectors": {x: list(v) for x, v in rank_vectors.items()}}]
    while len(elected) < seats:
        tally = {x: sum((w for b, w in zip(ballots, weights) if x in b["ranking"][:depth]), Fraction(0)) for x in c if x not in elected}
        eligible = [x for x in priority if x in tally and tally[x] >= quota]
        if not eligible:
            trace.append({"depth": depth, "tally": number_map(tally), "eligible": []})
            depth += 1
            continue
        winner = eligible[0]
        tied = [x for x in eligible if rank_vectors[x] == rank_vectors[winner]]
        tie |= len(tied) > 1
        elected.append(winner)
        factor = (tally[winner]-quota)/tally[winner]
        weights = [w*factor if winner in b["ranking"][:depth] else w for b, w in zip(ballots, weights)]
        trace.append({"depth": depth, "tally": number_map(tally), "eligible": eligible, "selected": winner, "tied": tied, "remainingWeights": [float(w) for w in weights]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'expanding-approvals', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_expanding_approvals(election["candidates"], election["ballots"], election["seats"], election["options"])
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

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
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

const election: Context = {
  "method": "expanding-approvals",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C",
        "D"
      ],
      "count": 6
    },
    {
      "ranking": [
        "C",
        "D",
        "A",
        "B"
      ],
      "count": 3
    },
    {
      "ranking": [
        "D",
        "C",
        "B",
        "A"
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
console.log(JSON.stringify(countExpandingApprovals(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/expanding-approvals.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/expanding-approvals.ts) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | pass | The stated quota lies in (N/(k+1), N/k], and the rule meets q-PSC demands on strict rankings. That entails Hare-PSC and its one-candidate solid-coalition consequence; this is not a theorem about arbitrary quota choices. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | pass | The stated quota lies in (N/(k+1), N/k], and the rule meets q-PSC demands on strict rankings. That entails Hare-PSC and its one-candidate solid-coalition consequence; this is not a theorem about arbitrary quota choices. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | fail | The EAR/QBS analysis distinguishes full candidate monotonicity from restricted rank-respecting improvements. Both general rules have candidate-monotonicity counterexamples for multiple seats. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | conditional | When every member of the balanced first-choice consensus set individually reaches q, its singleton coalition demands force all k members to be elected. General small-electorate cases need the quota condition; balanced first-choice counts alone are not silently assumed to reach q. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | unverified | Its quota changes with k, so nesting is not implied by the sequential form. No claim is transferred from the distinct candidate-monotonicity conditions studied for EAR. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | fail | For candidates A,B,C and two seats, BCA×1, CAB×14, CBA×12 elect &#123;B,C&#125;; tripling all counts elects &#123;A,C&#125;, without consequential ties. The additive epsilon in q changes the normalized quota and reweighting thresholds, so this exact variant is not homogeneous. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | If all voters share the same unordered top-k set W, its solid coalition demands all k seats under the stated q≤N/k. The rule’s q-PSC guarantee therefore forces exactly W, independently of its members’ internal rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | pass | If all voters share the same unordered top-k set W, its solid coalition demands all k seats under the stated q≤N/k. The rule’s q-PSC guarantee therefore forces exactly W, independently of its members’ internal rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | fail | A proportional coalition guarantee can require a seat for a substantial minority even when a strict majority shares another top-k set. For k≥3, both groups can exceed their first proportional seat threshold, contradicting a demand that every seat go to the majority’s set. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

Polynomial weighted prefix tallies; a straightforward bound is O((m+k)bm) arithmetic operations.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Aziz and Lee: EAR, Algorithm 1 and proportionality](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
