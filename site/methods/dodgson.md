# Dodgson’s method

Count the fewest adjacent ranking swaps needed to turn each candidate into a Condorcet winner. Prefer the smallest swap count.

**Ballot:** ranking. **API identifier:** `dodgson`.

## Counting rule

1. For a candidate, find the additional pairwise support needed against each rival.
2. Explore moving that candidate upward on individual ballots, charging one per adjacent swap.
3. Find the minimum total cost meeting every pairwise target. Compare these minimum costs across candidates.

**Variant used here:** Exact integer swaps on individual voters, not fractional swaps, an approximation, or a homogeneous variant.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

This smaller profile has three A > B > C ballots, two B > C > A ballots, and two C > B > A ballots. B already beats both rivals, so no swaps are needed. Seven voters fit the exact search limit.

```json
{
  "method": "dodgson",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C"
      ],
      "count": 3
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 2
    },
    {
      "ranking": [
        "C",
        "B",
        "A"
      ],
      "count": 2
    }
  ],
  "options": {
    "maxScore": 5,
    "budget": 100,
    "seed": 1
  }
}
```

The result is **B**. The trace records intermediate totals, eliminations, comparisons, or the lottery used by this rule.

```json
{
  "method": "dodgson",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "pairwise": {
        "A": {
          "A": 0,
          "B": 3,
          "C": 3
        },
        "B": {
          "A": 4,
          "B": 0,
          "C": 5
        },
        "C": {
          "A": 4,
          "B": 2,
          "C": 0
        }
      }
    },
    {
      "adjacentSwaps": {
        "A": 2,
        "B": 0,
        "C": 2
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Dodgson’s method — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def best(tally, minimum=False):
    value = (min if minimum else max)(tally.values())
    return [c for c in tally if tally[c] == value]

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_dodgson(c, ballots, options):
    p = pairwise(c, ballots)
    rankings = [b["ranking"] for b in ballots for _ in range(b["count"])]
    threshold = len(rankings)//2 + 1
    tally = {}
    for target in c:
        opponents = [x for x in c if x != target]
        needed = tuple(max(0, threshold-p[target][x]) for x in opponents)
        states = {tuple(0 for _ in opponents): 0}
        for ranking in rankings:
            position = ranking.index(target)
            choices = []
            for swaps in range(position+1):
                passed = set(ranking[position-swaps:position])
                choices.append((swaps, tuple(int(x in passed) for x in opponents)))
            updated = {}
            for gains, cost in states.items():
                for swaps, extra in choices:
                    new = tuple(min(needed[i], gains[i]+extra[i]) for i in range(len(opponents)))
                    updated[new] = min(updated.get(new, float("inf")), cost+swaps)
            states = updated
        tally[target] = states[needed]
    return result(best(tally, True), [{"pairwise": p}, {"adjacentSwaps": tally}])

election = {'method': 'dodgson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 3}, {'ranking': ['B', 'C', 'A'], 'count': 2}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_dodgson(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
```

```typescript
// Node 22.18+ (native TypeScript). Save as example.ts; run: node example.ts
// Self-contained count for valid input; the API also validates requests.
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

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
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

const election: Context = {
  "method": "dodgson",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C"
      ],
      "count": 3
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 2
    },
    {
      "ranking": [
        "C",
        "B",
        "A"
      ],
      "count": 2
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 7
};
console.log(JSON.stringify(countDodgson(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/dodgson.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/dodgson.ts) file. The complete engines use the same functions.

## Simulate this method through HTTP

Start the server from the repository with `python3 python/server.py`. Save the request above as `election.json`, then run:

```sh
curl --fail-with-body http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @election.json
```

The server runs the Python algorithm and returns the JSON shown above. GitHub Pages itself does not execute API requests. See the [request and error reference](/api-design.md).

## Criteria and assumptions

These are properties of rules over whole classes of elections, not conclusions proved by the worked example. **Pass** and **fail** refer to the stated mathematical interpretation; **conditional** requires the stated assumptions; **unverified** means this guide has not established a result; **not-applicable** means the criterion is not defined for this input or outcome model. A fixed priority can change properties at exact ties. See the [definitions and interpretation guide](/criteria.md) before comparing rows.

| Criterion | Assessment | Explanation and evidence |
| --- | --- | --- |
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Weak Pareto](/criteria.md#weak-pareto) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Strong Pareto](/criteria.md#strong-pareto) | unverified | On complete strict rankings, weak and strong Pareto have the same test. Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Monotonicity](/criteria.md#monotonicity) | fail | Extra support can change a later contest or search score so that a previous winner loses. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | fail | A previous unique winner can remain a unique winner after all rankings are reversed. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Homogeneity](/criteria.md#homogeneity) | fail | Integer swap requirements can change the winning comparison when all voters are replicated. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Polynomial counting time](/criteria.md#polynomial-time) | fail | This exact algorithm is exponential or factorial. The unrestricted winner problem is computationally hard; the small input cap is not a polynomial-time algorithm. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Resolvability](/criteria.md#resolvability) | unverified | No asymptotic tie-frequency theorem is asserted for this exact variant. A fixed priority or seed makes execution repeatable but does not prove resolvability. [Source](https://arxiv.org/abs/1804.02973). |
| [Summability](/criteria.md#summability) | pass | A histogram of all complete ranking types is additive but can contain m! entries. Small candidate totals or the original pairwise matrix generally do not capture future transfers or swap costs. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |

## Cost and limits

Exponential search in voters and candidates; computationally difficult on unrestricted elections.

At most 5 candidates and 8 represented voters; larger inputs return HTTP 413. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Brandt: Some Remarks on Dodgson’s Voting Rule](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf)
- [Handbook of Computational Social Choice](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
