# Bucklin voting

Expand the number of ranked positions counted until somebody reaches a strict majority, then prefer the largest cumulative total.

**Ballot:** ranking. **API identifier:** `bucklin`.

## Counting rule

1. Start by counting only first places.
2. If nobody has more than half the voters, count first and second places, then increase depth again.
3. At the first successful depth, return the candidates with the largest cumulative support.

**Variant used here:** Ordinary Bucklin with complete strict rankings; the first majority depth matters.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "bucklin",
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
      "count": 4
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 3
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
  "method": "bucklin",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "depth": 1,
      "tally": {
        "A": 4,
        "B": 3,
        "C": 2
      }
    },
    {
      "depth": 2,
      "tally": {
        "A": 4,
        "B": 9,
        "C": 5
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Bucklin voting — complete algorithm">

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

def count_bucklin(c, ballots, options):
    tally = dict.fromkeys(c, 0)
    total = sum(b["count"] for b in ballots)
    trace = []
    for depth in range(len(c)):
        for b in ballots:
            tally[b["ranking"][depth]] += b["count"]
        trace.append({"depth": depth+1, "tally": tally.copy()})
        if max(tally.values())*2 > total:
            return result(best(tally), trace)
    return result(best(tally), trace)

election = {'method': 'bucklin', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_bucklin(election["candidates"], election["ballots"], election["options"])
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

export function countBucklin(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  const trace: Trace = [];
  for (let depth = 1; depth <= ctx.candidates.length; depth++) {
    for (const b of ctx.ballots) tally[b.ranking![depth - 1]] += b.count;
    trace.push({depth, tally: {...tally}});
    if (Math.max(...Object.values(tally)) * 2 > ctx.total) break;
  }
  return result(ctx, best(ctx.candidates, tally), trace);
}

const election: Context = {
  "method": "bucklin",
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
      "count": 4
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 3
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
  "total": 9
};
console.log(JSON.stringify(countBucklin(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/bucklin.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/bucklin.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | A majority agreeing on a preferred group keeps the winner within that group. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | fail | A previous unique winner can remain a unique winner after all rankings are reversed. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm + m²) when each depth adds one position per ballot. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Summability](/criteria.md#summability) | pass | O(m²) candidate-by-rank counts are enough to rebuild each depth total. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [Later no help](/criteria.md#later-no-help) | pass | Adding a lower preference cannot improve an already higher candidate’s outcome under the standard interpretation. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pref-voting.readthedocs.io/en/stable/other_methods.html). |

## Cost and limits

O(bm + m²) when each depth adds one position per ballot.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Other methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/other_methods.html)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
