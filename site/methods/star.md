# STAR voting

Use scores to choose two finalists, then count which finalist each voter scored higher.

**Ballot:** scores. **API identifier:** `star`.

## Counting rule

1. Sum all grades and advance the two greatest totals.
2. On every ballot give one runoff vote to its higher-graded finalist; equal grades abstain in this comparison.
3. Return the finalist with greater runoff support, or both if tied.

**Variant used here:** Score then automatic runoff on a zero-to-maxScore scale; finalist score ties use fixed candidate priority rather than the full official tiebreak protocol.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "star",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "scores": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 5
      },
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
  "method": "star",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "stage": "score",
      "tally": {
        "A": 20,
        "B": 32,
        "C": 19
      },
      "finalists": [
        "B",
        "A"
      ]
    },
    {
      "stage": "runoff",
      "tally": {
        "B": 5,
        "A": 4
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="STAR voting — complete algorithm">

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

def count_star(c, ballots, options):
    tally = {x: sum(b["scores"][x]*b["count"] for b in ballots) for x in c}
    finalists = sorted(c, key=lambda x: -tally[x])[:2]
    trace = [{"stage": "score", "tally": tally, "finalists": finalists}]
    if len(finalists) == 1:
        return result(finalists, trace)
    a, b = finalists
    runoff = {a: sum(v["count"] for v in ballots if v["scores"][a] > v["scores"][b]), b: sum(v["count"] for v in ballots if v["scores"][b] > v["scores"][a])}
    trace.append({"stage": "runoff", "tally": runoff})
    return result([x for x in c if x in best(runoff)], trace)

election = {'method': 'star', 'candidates': ['A', 'B', 'C'], 'ballots': [{'scores': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'scores': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'scores': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_star(election["candidates"], election["ballots"], election["options"])
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

export function countStar(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.scores![c] * b.count;
  const finalists = [...ctx.candidates].sort((a, b) => tally[b] - tally[a] || ctx.candidates.indexOf(a) - ctx.candidates.indexOf(b)).slice(0, 2);
  const runoff = zeros(finalists);
  if (finalists.length === 2) for (const b of ctx.ballots) {
    const [a, c] = finalists;
    if (b.scores![a] > b.scores![c]) runoff[a] += b.count;
    if (b.scores![c] > b.scores![a]) runoff[c] += b.count;
  }
  return result(ctx, best(finalists, runoff), finalists.length === 1 ? [{stage: 'score', tally, finalists}] : [{stage: 'score', tally, finalists}, {stage: 'runoff', tally: runoff}]);
}

const election: Context = {
  "method": "star",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "scores": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "scores": {
        "A": 0,
        "B": 4,
        "C": 5
      },
      "count": 2
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 9
};
console.log(JSON.stringify(countStar(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/star.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/star.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://www.starvoting.org/). |
| [Rated majority](/criteria.md#majority-rated) | fail | A maximum-rated majority favorite can miss the finalist cut: 51×(A5,B4,C4),49×(A0,B5,C5) gives B and C the two largest totals. [Source](https://www.starvoting.org/). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://www.starvoting.org/). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://www.starvoting.org/). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://www.starvoting.org/). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | The standard rule excludes a candidate losing every pairwise comparison. [Source](https://www.starvoting.org/). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | Unanimous strict preference prevents the dominated candidate winning on the stated ballot domain. [Source](https://www.starvoting.org/). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | Submitted weak grade dominance with one strict improvement gives A a larger sum than B. B cannot pass the finalist cut without A; in their runoff at least one voter prefers A and none prefers B. [Source](https://www.starvoting.org/). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://www.starvoting.org/). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://www.starvoting.org/). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://www.starvoting.org/). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://www.starvoting.org/). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://www.starvoting.org/). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://www.starvoting.org/). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://www.starvoting.org/). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://www.starvoting.org/). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://www.starvoting.org/). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | fail | A previous unique winner can remain a unique winner after all rankings are reversed. [Source](https://www.starvoting.org/). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://www.starvoting.org/). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm + m log m). [Source](https://www.starvoting.org/). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://www.starvoting.org/). |
| [Summability](/criteria.md#summability) | pass | O(m²) pairwise totals are additive; Borda totals for Black and score totals for STAR add only O(m). Kemeny’s difficult optimization still occurs after aggregation. [Source](https://www.starvoting.org/). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://www.starvoting.org/). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://www.starvoting.org/). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://www.starvoting.org/). |

## Cost and limits

O(bm + m log m).

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [STAR Voting: counting and ballot instructions](https://www.starvoting.org/)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
