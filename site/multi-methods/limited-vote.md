# Limited voting

Each voter may mark fewer candidates than seats. The largest candidate mark totals win, leaving voters fewer marks than a full bloc ballot.

**Ballot:** approvals. **API identifier:** `limited-vote` at `/multi/simulate`.

## Counting rule

1. Choose an explicit per-ballot mark limit.
2. Validate that each approval subset contains at most that many candidates, and count its marks.
3. Elect the k largest candidate totals.

**Implemented variant:** At-most-limit positive marks, with limit default max(1,k−1). To compare committee sizes while holding the ballot rule fixed, explicitly keep the same limit. The k=1 default is the usual one-mark boundary case.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "limited-vote",
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
        "A"
      ],
      "count": 6
    },
    {
      "approvals": [
        "C"
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

**The selected committee is A and C.** Each voter can mark at most one candidate in this two-seat example. A receives six marks, C three, and D one, so A and C win. Approvals here are supplied explicitly rather than inferred from a ranking.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "limited-vote",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "tally": {
        "A": 6,
        "B": 0,
        "C": 3,
        "D": 1
      }
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Limited voting — complete algorithm">

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

def count_approval(c, ballots, seats, options):
    tally = {x: sum(b["count"] for b in ballots if x in b["approvals"]) for x in c}
    return tally_result(c, tally, seats)

def count_limited_vote(c, ballots, seats, options):
    return count_approval(c, ballots, seats, options)

election = {'method': 'limited-vote', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'approvals': ['A'], 'count': 6}, {'approvals': ['C'], 'count': 3}, {'approvals': ['D'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_limited_vote(election["candidates"], election["ballots"], election["seats"], election["options"])
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

export function countApproval(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) for (const c of ballot.approvals!) tally[c] += ballot.count;
  const {winners, tie} = selectTop(ctx.candidates, tally, ctx.seats);
  return result(ctx, winners, tie, [{tally}]);
}

export function countLimitedVote(ctx: Context): SimulationResult {
  return countApproval(ctx);
}

const election: Context = {
  "method": "limited-vote",
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
        "A"
      ],
      "count": 6
    },
    {
      "approvals": [
        "C"
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
console.log(JSON.stringify(countLimitedVote(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/limited-vote.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/limited-vote.ts) program.

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
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | conditional | For an explicitly fixed mark limit, candidate totals and their ranking do not change with k. The default limit=max(1,k−1) changes the ballot restriction, so comparisons using changed defaults do not hold the voting rule fixed. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | conditional | With fixed submitted marks and an explicit fixed mark limit, deleting an unelected candidate leaves all remaining totals unchanged. A voter replacing the deleted mark is a changed ballot. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | pass | For a fixed k and fixed ballot rule, each committee’s objective is a sum of candidate totals, which themselves add over electorates. Common maximizing committees remain exactly the common maximizers after addition; fixed priority selects consistently. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | O(m) candidate totals add across precincts and suffice for this fixed seat count and ballot rule. For Bloc, recomputing a different k requires new top-k totals or richer data. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(bm + m log m).

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Lackner and Skowron: approval rules and ballot restrictions](https://arxiv.org/abs/2007.01795)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
