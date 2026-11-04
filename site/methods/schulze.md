# Schulze (beatpaths)

A path from A to B is as strong as its weakest victory. Compare the strongest available path in each direction.

**Ballot:** ranking. **API identifier:** `schulze`.

## Counting rule

1. Create a directed edge only for a strict pairwise victory, weighted by support for its winner.
2. For every pair, find the largest bottleneck strength over all paths.
3. Keep candidates whose strongest path to each rival is at least as strong as the reverse path.

**Variant used here:** Winning-votes beatpath strengths and the standard max–min path update.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "schulze",
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
  "method": "schulze",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "pairwise": {
        "A": {
          "A": 0,
          "B": 4,
          "C": 4
        },
        "B": {
          "A": 5,
          "B": 0,
          "C": 7
        },
        "C": {
          "A": 5,
          "B": 2,
          "C": 0
        }
      }
    },
    {
      "strongestPaths": {
        "A": {
          "A": 0,
          "B": 0,
          "C": 0
        },
        "B": {
          "A": 5,
          "B": 0,
          "C": 7
        },
        "C": {
          "A": 5,
          "B": 0,
          "C": 0
        }
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Schulze (beatpaths) — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_schulze(c, ballots, options):
    p = pairwise(c, ballots)
    paths = {x: {y: p[x][y] if x != y and p[x][y] > p[y][x] else 0 for y in c} for x in c}
    for middle in c:
        for start in c:
            for end in c:
                if len({start, middle, end}) == 3:
                    paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
    winners = [x for x in c if all(paths[x][y] >= paths[y][x] for y in c)]
    return result(winners, [{"pairwise": p}, {"strongestPaths": paths}])

election = {'method': 'schulze', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_schulze(election["candidates"], election["ballots"], election["options"])
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

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

export function countSchulze(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const paths = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const c of ctx.candidates) for (const d of ctx.candidates) if (matrix[c][d] > matrix[d][c]) paths[c][d] = matrix[c][d];
  for (const via of ctx.candidates) for (const from of ctx.candidates) if (from !== via) for (const to of ctx.candidates) if (to !== via && to !== from)
    paths[from][to] = Math.max(paths[from][to], Math.min(paths[from][via], paths[via][to]));
  return result(ctx, ctx.candidates.filter(c => ctx.candidates.every(d => c === d || paths[c][d] >= paths[d][c])), [{pairwise: matrix}, {strongestPaths: paths}]);
}

const election: Context = {
  "method": "schulze",
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
console.log(JSON.stringify(countSchulze(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/schulze.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/schulze.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://arxiv.org/abs/1804.02973). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://arxiv.org/abs/1804.02973). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://arxiv.org/abs/1804.02973). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | A majority agreeing on a preferred group keeps the winner within that group. [Source](https://arxiv.org/abs/1804.02973). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://arxiv.org/abs/1804.02973). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | The standard rule excludes a candidate losing every pairwise comparison. [Source](https://arxiv.org/abs/1804.02973). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://arxiv.org/abs/1804.02973). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://arxiv.org/abs/1804.02973). |
| [Smith set](/criteria.md#smith) | pass | The standard rule chooses only from the smallest strictly majority-dominant set. [Source](https://arxiv.org/abs/1804.02973). |
| [Smith independence](/criteria.md#smith-iia) | pass | Removing Smith outsiders does not alter the retained outcome in the standard rule. [Source](https://arxiv.org/abs/1804.02973). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://arxiv.org/abs/1804.02973). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://arxiv.org/abs/1804.02973). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://arxiv.org/abs/1804.02973). |
| [Independence of clones](/criteria.md#clone-independence) | pass | The standard rule preserves outsider and clone-group winning status. [Source](https://arxiv.org/abs/1804.02973). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://arxiv.org/abs/1804.02973). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://arxiv.org/abs/1804.02973). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://arxiv.org/abs/1804.02973). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | pass | Reversing every strict preference excludes a former unique winner under the standard interpretation. [Source](https://arxiv.org/abs/1804.02973). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://arxiv.org/abs/1804.02973). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm² + m³) time and O(m²) tally/path storage. [Source](https://arxiv.org/abs/1804.02973). |
| [Resolvability](/criteria.md#resolvability) | pass | Schulze proves resolvability for the mathematical rule; final exact ties are still returned as co-winners. [Source](https://arxiv.org/abs/1804.02973). |
| [Summability](/criteria.md#summability) | pass | O(m²) pairwise totals are additive; Borda totals for Black and score totals for STAR add only O(m). Kemeny’s difficult optimization still occurs after aggregation. [Source](https://arxiv.org/abs/1804.02973). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://arxiv.org/abs/1804.02973). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://arxiv.org/abs/1804.02973). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://arxiv.org/abs/1804.02973). |

## Cost and limits

O(bm² + m³) time and O(m²) tally/path storage.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Markus Schulze: The Schulze Method of Voting](https://arxiv.org/abs/1804.02973)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
