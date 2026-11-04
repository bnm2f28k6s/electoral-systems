# Single transferable vote (STV)

Voters rank candidates. Quota winners retain enough vote weight for a seat, surplus weight transfers, and the lowest remaining candidate is eliminated when nobody reaches quota.

**Ballot:** ranking. **API identifier:** `stv` at `/multi/simulate`.

## Counting rule

1. Set the integer Droop quota to floor(N/(k+1)) + 1. Each ballot starts with weight 1.
2. Give each continuing ballot to its highest-ranked continuing candidate. Elect a quota-reaching candidate and transfer its surplus proportionally across all ballots currently assigned to it.
3. If nobody reaches quota, eliminate a lowest-total candidate and transfer those ballots. Elect all remaining candidates when they exactly fill the unfilled seats.

**Implemented variant:** Weighted inclusive Gregory surplus transfers with exact fractions, complete strict rankings, and integer Droop quota. Election laws and other STV implementations use different transfer and tie rules.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "stv",
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

**The selected committee is A and C.** The integer Droop quota is four. A starts with six votes, keeps four, and transfers a surplus of two to B. D has only one vote and is eliminated; that ballot transfers to C, who now has four and takes the second seat.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "stv",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "quota": 4
    },
    {
      "tally": {
        "A": 6.0,
        "B": 0.0,
        "C": 3.0,
        "D": 1.0
      },
      "elected": "A",
      "tied": [
        "A"
      ],
      "transferFactor": 0.3333333333333333
    },
    {
      "tally": {
        "B": 2.0,
        "C": 3.0,
        "D": 1.0
      },
      "eliminated": "D",
      "tied": [
        "D"
      ]
    },
    {
      "tally": {
        "B": 2.0,
        "C": 4.0
      },
      "elected": "C",
      "tied": [
        "C"
      ],
      "transferFactor": 0.0
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Single transferable vote (STV) — complete algorithm">

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

def count_stv(c, ballots, seats, options):
    quota = sum(b["count"] for b in ballots)//(seats+1)+1
    weights = [Fraction(b["count"]) for b in ballots]
    active, elected, trace, tie = c[:], [], [{"quota": quota}], False
    while len(elected) < seats:
        if len(active) == seats-len(elected):
            elected.extend(active)
            trace.append({"electedRemaining": active[:]})
            break
        choices = [next(x for x in b["ranking"] if x in active) for b in ballots]
        tally = {x: sum((w for choice, w in zip(choices, weights) if choice == x), Fraction(0)) for x in active}
        eligible = [x for x in active if tally[x] >= quota]
        if eligible:
            high = max(tally[x] for x in eligible)
            tied = [x for x in eligible if tally[x] == high]
            winner = tied[0]
            tie |= len(tied) > 1
            factor = (tally[winner]-quota)/tally[winner]
            weights = [w*factor if choice == winner else w for choice, w in zip(choices, weights)]
            elected.append(winner)
            active.remove(winner)
            trace.append({"tally": number_map(tally), "elected": winner, "tied": tied, "transferFactor": float(factor)})
        else:
            low = min(tally.values())
            tied = [x for x in active if tally[x] == low]
            loser = tied[-1]
            tie |= len(tied) > 1
            active.remove(loser)
            trace.append({"tally": number_map(tally), "eliminated": loser, "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
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

const election: Context = {
  "method": "stv",
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
console.log(JSON.stringify(countStv(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/stv.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/stv.ts) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | conditional | PSC-style guarantees depend on the quota, fractional transfers and boundary cases. This implementation uses integer Droop and exact Gregory fractions; unrounded-quota theorems are not silently transferred to all small electorates. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | conditional | PSC-style guarantees depend on the quota, fractional transfers and boundary cases. This implementation uses integer Droop and exact Gregory fractions; unrounded-quota theorems are not silently transferred to all small electorates. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | fail | A raised candidate can alter the order of eliminations and later transfers and thereby lose a seat; the failure occurs already in the one-seat IRV special case. [Source](https://arxiv.org/abs/1506.02891). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | fail | The quota and representation demands change with the number of seats, so a new count can replace a previously elected candidate. Published counterexamples establish failure for the standard rule. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | fail | Combining electorates can change quota crossings and elimination/transfer order. Standard STV admits failures; a common final committee is not protected by an additive objective. [Source](https://arxiv.org/abs/1506.02891). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | fail | With candidates A,B,C,D and three seats, ballots BCAD×1, DABC×5, BDCA×7 elect &#123;A,B,D&#125;. Tripling every count elects &#123;B,C,D&#125;, with no consequential ties in either run. Integer Droop rounding changes quota share and transfer fractions; this implementation is not homogeneous. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | fail | With priority order D,C,B,A, three seats and one A&gt;B&gt;C&gt;D ballot, integer Droop is 1 and the implementation selects &#123;A,C,D&#125;, not the unanimous top set &#123;A,B,C&#125;. Zero-weight or equal-comparison ties after retaining A’s quota expose the small-electorate failure. Unrounded-quota theorems do not prove this accepted-input variant strongly unanimous. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

At most m selection or elimination rounds; straightforward repeated ranking scans cost O(bm²) arithmetic operations.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Elkind et al.: properties and variants of STV](https://arxiv.org/abs/1506.02891)
- [Aziz and Lee: quotas, PSC, and transfer assumptions](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
