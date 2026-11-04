# Multi-winner sortition

Select a uniformly random size-k subset of the candidate list. Voter preferences do not affect selection.

**Ballot:** none. **API identifier:** `sortition` at `/multi/simulate`.

## Counting rule

1. Start with all candidates available.
2. For each seat, draw uniformly from remaining candidates, then remove the selected candidate.
3. Return the selected set in candidate-list order, with the draw trace.

**Implemented variant:** Uniform committee sampling without replacement, using the shared seeded generator for reproducibility. It samples candidate IDs, not a real-world citizen register.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "sortition",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "ballots": [],
  "options": {
    "maxScore": 5,
    "budget": 100,
    "limit": 1,
    "seed": 1
  }
}
```

**The selected committee is A and C.** With seed one, the first uniform draw selects A. The second uniform draw from B, C, and D selects C. Every two-candidate committee has the same mathematical probability; these two names are one reproducible sample.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "sortition",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "round": 1,
      "probabilities": {
        "A": 0.25,
        "B": 0.25,
        "C": 0.25,
        "D": 0.25
      },
      "selected": "A",
      "state": 1015568748
    },
    {
      "round": 2,
      "probabilities": {
        "B": 0.3333333333333333,
        "C": 0.3333333333333333,
        "D": 0.3333333333333333
      },
      "selected": "C",
      "state": 1586005467
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Multi-winner sortition — complete algorithm">

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

def draw(c, tally, seed):
    state = (1664525*seed+1013904223) % 2**32
    total = sum(tally.values())
    threshold, cumulative = Fraction(state, 2**32), Fraction(0)
    probabilities = {x: Fraction(tally[x], total) for x in c}
    for x in c:
        cumulative += probabilities[x]
        if threshold < cumulative:
            return x, state, number_map(probabilities)
    return c[-1], state, number_map(probabilities)

def count_sortition(c, ballots, seats, options):
    active, elected, trace, seed = c[:], [], [], options["seed"]
    for step in range(seats):
        winner, seed, probabilities = draw(active, dict.fromkeys(active, 1), seed)
        elected.append(winner)
        active.remove(winner)
        trace.append({"round": step+1, "probabilities": probabilities, "selected": winner, "state": seed})
    return {"winners": ordered(c, elected), "tie": False, "trace": trace}

election = {'method': 'sortition', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_sortition(election["candidates"], election["ballots"], election["seats"], election["options"])
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

function gcd(a: bigint, b: bigint): bigint {while (b) {const next = b; b = a % b; a = next;} return a < 0n ? -a : a;}

function fraction(n: number | bigint, d: number | bigint = 1): Fraction {
  let a = BigInt(n), b = BigInt(d); if (b < 0n) {a = -a; b = -b;} const g = gcd(a, b); return [a / g, b / g];
}

function add(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);}

function compare(a: Fraction, b: Fraction): number {const d = a[0] * b[1] - b[0] * a[1]; return d < 0n ? -1 : d > 0n ? 1 : 0;}
/** Round an exact rational to a JSON-display number without BigInt overflow.
 * Election decisions use compare(), never this floating-point conversion.
 */

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
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

const election: Context = {
  "method": "sortition",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [],
  "maxScore": 5,
  "budget": 100,
  "limit": 1,
  "seed": 1,
  "total": 0
};
console.log(JSON.stringify(countSortition(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/sortition.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/sortition.ts) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | not-applicable | No voter support appears in the input. The distribution is unchanged by imagined preference changes, which is a vacuous invariance rather than a support guarantee. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | conditional | With the same seed and fixed candidate and ballot order, the size-(k+1) run extends the size-k draw sequence, so sampled committees are nested. A distributional axiom comparing all co-winning outcomes needs its own interpretation. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | fail | Removing an unelected candidate changes the uniform committee distribution. A single unchanged sampled result cannot establish independence of the underlying lottery. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | not-applicable | There are no voter electorates to combine. Its fixed candidate distribution is independent of ballots; this does not establish a voting-rule consistency theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | not-applicable | There is no submitted electorate to replicate. The candidate-subset distribution does not depend on any ballot counts. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | not-applicable | No ballot is submitted, so there is no favorite-ranking strategy to choose. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | not-applicable | There is no strategic ballot or best-response ballot domain. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | fail | A universally liked candidate is included with probability k/m, not guaranteed a seat, when k&lt;m. The method does not observe likes. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | fail | Uniform candidate sampling can elect a committee violating this preference-based requirement with positive probability. It has no mechanism to protect voter support or dominance. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | not-applicable | Sortition does not count voter ballots; only the candidate list, seat count and draw procedure are used. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(km) with straightforward list removal; the conceptual distribution has binomial(m,k) committees.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Probabilistic social-choice models and sampling](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
