# Multi-winner minimax (Simpson)

Give each candidate their weakest head-to-head support count, then elect the k candidates with the highest such scores.

**Ballot:** ranking. **API identifier:** `minimax` at `/multi/simulate`.

## Counting rule

1. Build the pairwise support matrix p(a,b): how many voters prefer a to b.
2. For each candidate a, take min over every other b of p(a,b).
3. Elect the k greatest candidate minima, using priority at a tied cutoff.

**Implemented variant:** The Simpson committee selection rule S. This is top-k candidate maximin support; it does not optimize the boundary of a whole committee and is not the single-winner demo’s clipped-margin score.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "minimax",
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

**The selected committee is A and C.** A's weakest head-to-head support is six voters, C's is four, and B's and D's are one each. Choosing the two strongest individual worst-case totals elects A and C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "minimax",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "pairwise": {
        "A": {
          "A": 0,
          "B": 9,
          "C": 6,
          "D": 6
        },
        "B": {
          "A": 1,
          "B": 0,
          "C": 6,
          "D": 6
        },
        "C": {
          "A": 4,
          "B": 4,
          "C": 0,
          "D": 9
        },
        "D": {
          "A": 4,
          "B": 4,
          "C": 1,
          "D": 0
        }
      }
    },
    {
      "simpsonScores": {
        "A": 6,
        "B": 1,
        "C": 4,
        "D": 1
      }
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Multi-winner minimax (Simpson) — complete algorithm">

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

def select_top(c, tally, seats):
    ranked = sorted(c, key=lambda x: -tally[x])
    cutoff = tally[ranked[seats-1]]
    tie = any(tally[x] == cutoff for x in ranked[seats:])
    return ordered(c, ranked[:seats]), tie

def tally_result(c, tally, seats, label="tally"):
    winners, tie = select_top(c, tally, seats)
    return {"winners": winners, "tie": tie, "trace": [{label: number_map(tally)}]}

def pairwise(c, ballots):
    matrix = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                matrix[x][y] += b["count"]
    return matrix

def count_minimax(c, ballots, seats, options):
    matrix = pairwise(c, ballots)
    total = sum(b["count"] for b in ballots)
    tally = {x: min([matrix[x][y] for y in c if y != x] or [total]) for x in c}
    counted = tally_result(c, tally, seats, "simpsonScores")
    counted["trace"].insert(0, {"pairwise": matrix})
    return counted

election = {'method': 'minimax', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_minimax(election["candidates"], election["ballots"], election["seats"], election["options"])
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

export function countMinimax(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const tally = Object.fromEntries(ctx.candidates.map(c => [c, ctx.candidates.length > 1 ? Math.min(...ctx.candidates.filter(x => x !== c).map(x => matrix[c][x])) : ctx.total]));
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{pairwise: matrix}, {simpsonScores: tally}]);
}

const election: Context = {
  "method": "minimax",
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
console.log(JSON.stringify(countMinimax(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/minimax.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/minimax.ts) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | pass | Increasing one elected candidate’s own support cannot worsen its compared score relative to opponents. In the reweighted sequential rule it can move the candidate to an earlier election round; it does not require retaining the same other winners. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | pass | Under the ordinal replacement test, unanimous A above B ensures that a winning outcome including B does not exclude A from every possible winning committee. Fixed priority may select just one member of that correspondence. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | fail | With every voter ranking A &gt; B &gt; C and two seats, B and C both have worst-pairwise support zero. &#123;A,C&#125; can be co-optimal even though every voter prefers B to C. Simpson’s weak property does not imply this strong one. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | fail | Balanced first-choice support need not determine positional totals or weakest pairwise contests. The cited ordinal analyses provide consensus-committee failures. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | fail | Scoring a candidate against all rivals can penalize contests inside the intended committee. The best-k Simpson rule need not select a Gehrlein committee even when one exists. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | pass | The underlying candidate ranking is independent of k. Keeping the same candidate priority and other options, taking its first k and first k+1 yields nested committees. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | fail | Taking a minimum is not an additive committee objective. The primary comparison proves failure for both the Simpson and committee Maximin correspondences. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | The unanimously top-ranked k-set belongs to the standard co-winning correspondence, but zero first-choice or weakest-contest scores can admit other committees too. The API’s fixed selector can choose a different committee at such a tie; this is not a strong-unanimity guarantee. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | fail | Unanimity need not distinguish every top-set member from an outsider. For A &gt; B &gt; C on every ballot with two seats, a zero-score tie can admit &#123;A,C&#125; as well as &#123;A,B&#125;. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | fail | A majority supporting the same top-k set need not give every member a sufficiently high positional, first-choice or worst-contest score. These rules do not provide the fixed-majority committee guarantee. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | The O(m²) pairwise-support matrix adds across precincts and determines all candidate or committee minima. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(bm² + m² + m log m).

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Bubboloni, Diss and Gori: Simpson and Maximin committee rules](https://flore.unifi.it/handle/2158/1175914)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
