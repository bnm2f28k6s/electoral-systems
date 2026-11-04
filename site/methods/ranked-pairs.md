# Ranked pairs

Consider stronger head-to-head victories first. Keep a victory unless it would create a directed cycle.

**Ballot:** ranking. **API identifier:** `ranked-pairs`.

## Counting rule

1. Sort strict pairwise victories by the number voting for their winner.
2. Lock each victory unless there is already a path from its loser back to its winner.
3. Return candidates with no incoming locked defeat.

**Variant used here:** Winning-votes strength; equal strengths use candidate input priority. Other strength or tie policies can change the result.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "ranked-pairs",
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
  "method": "ranked-pairs",
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
      "edges": [
        {
          "from": "B",
          "to": "C",
          "strength": 7,
          "locked": true
        },
        {
          "from": "B",
          "to": "A",
          "strength": 5,
          "locked": true
        },
        {
          "from": "C",
          "to": "A",
          "strength": 5,
          "locked": true
        }
      ]
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Ranked pairs — complete algorithm">

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

def count_ranked_pairs(c, ballots, options):
    p = pairwise(c, ballots)
    edges = [(x, y) for x in c for y in c if p[x][y] > p[y][x]]
    # Stable ties: winning votes descending, then candidate input order.
    edges.sort(key=lambda edge: -p[edge[0]][edge[1]])
    graph = {x: [] for x in c}
    decisions = []
    def reachable(start, target):
        pending, seen = [start], set()
        while pending:
            x = pending.pop()
            if x == target:
                return True
            if x not in seen:
                seen.add(x)
                pending.extend(graph[x])
        return False
    for x, y in edges:
        locked = not reachable(y, x)
        if locked:
            graph[x].append(y)
        decisions.append({"from": x, "to": y, "strength": p[x][y], "locked": locked})
    winners = [x for x in c if not any(x in graph[y] for y in c)]
    return result(winners, [{"pairwise": p}, {"edges": decisions}])

election = {'method': 'ranked-pairs', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_ranked_pairs(election["candidates"], election["ballots"], election["options"])
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

function reachable(edges: Record<string, string[]>, from: string, target: string): boolean {
  const seen = new Set<string>();
  const stack = [from];
  while (stack.length) { const c = stack.pop()!; if (c === target) return true; if (!seen.has(c)) { seen.add(c); stack.push(...edges[c]); } }
  return false;
}

export function countRankedPairs(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const edges = Object.fromEntries(ctx.candidates.map(c => [c, [] as string[]]));
  const victories: [string, string][] = [];
  for (const c of ctx.candidates) for (const d of ctx.candidates) if (matrix[c][d] > matrix[d][c]) victories.push([c, d]);
  victories.sort(([a, b], [c, d]) => matrix[c][d] - matrix[a][b] || ctx.candidates.indexOf(a) - ctx.candidates.indexOf(c) || ctx.candidates.indexOf(b) - ctx.candidates.indexOf(d));
  const decisions: Record<string, unknown>[] = [];
  for (const [winner, loser] of victories) {
    const locked = !reachable(edges, loser, winner);
    if (locked) edges[winner].push(loser);
    decisions.push({from: winner, to: loser, strength: matrix[winner][loser], locked});
  }
  return result(ctx, ctx.candidates.filter(c => ctx.candidates.every(d => !edges[d].includes(c))), [{pairwise: matrix}, {edges: decisions}]);
}

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

const election: Context = {
  "method": "ranked-pairs",
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
console.log(JSON.stringify(countRankedPairs(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/ranked-pairs.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/ranked-pairs.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | A majority agreeing on a preferred group keeps the winner within that group. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | The standard rule excludes a candidate losing every pairwise comparison. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Smith set](/criteria.md#smith) | pass | The standard rule chooses only from the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | pass | Removing Smith outsiders does not alter the retained outcome in the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | conditional | LIIA is a property of the standard social-ordering version, subject to consistent tie treatment. This API returns only winners, so it does not directly expose that ordering. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | conditional | Clone independence depends on how equal victory strengths are ordered. This demo’s fixed priority is not the special Zavist–Tideman tie rule, so no all-profile guarantee is claimed. [Source](https://www.condorcet.vote/assets/DOCS/CompleteIndependenceofClones.pdf). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | The standard rule has reversal-symmetry results with appropriate tie conventions; fixed ordering of equal-strength victories needs separate analysis. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm² + m⁴) using a graph search for each of O(m²) victories. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Summability](/criteria.md#summability) | pass | O(m²) pairwise totals are additive; Borda totals for Black and score totals for STAR add only O(m). Kemeny’s difficult optimization still occurs after aggregation. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html). |

## Cost and limits

O(bm² + m⁴) using a graph search for each of O(m²) victories.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Margin methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/margin_based_methods.html)
- [Markus Schulze: The Schulze Method of Voting](https://arxiv.org/abs/1804.02973)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
