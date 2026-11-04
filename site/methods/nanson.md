# Nanson’s method

Repeatedly remove candidates whose Borda points are at or below the current average.

**Ballot:** ranking. **API identifier:** `nanson`.

## Counting rule

1. With k candidates left, assign k−1 points to first place down to zero for last.
2. Recompute the average candidate total and eliminate all candidates at or below it.
3. Repeat; if every remaining candidate has the same total, return their tie.

**Variant used here:** Non-strict Nanson: eliminate at or below the average, rather than only below it.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "nanson",
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
  "method": "nanson",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "active": [
        "A",
        "B",
        "C"
      ],
      "tally": {
        "A": 8,
        "B": 12,
        "C": 7
      },
      "eliminated": [
        "A",
        "C"
      ]
    },
    {
      "active": [
        "B"
      ]
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Nanson’s method — complete algorithm">

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

def first_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        choice = b.get("choice") or next(x for x in b["ranking"] if x in active)
        tally[choice] += b["count"]
    return tally

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        ranking = [x for x in b["ranking"] if x in active]
        for position, x in enumerate(ranking):
            tally[x] += (len(c) - position - 1) * b["count"]
    return tally

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def smith_set(c, p):
    # Closure adds every outsider not strictly beaten by each current member.
    closures = []
    for start in c:
        group = {start}
        while True:
            expanded = group | {y for y in c if any(p[x][y] <= p[y][x] for x in group if x != y)}
            if expanded == group:
                break
            group = expanded
        closures.append(group)
    smallest = min(closures, key=len)
    return [x for x in c if x in smallest]

def elimination(c, ballots, mode):
    active = c[:]
    trace = []
    total = sum(b["count"] for b in ballots)
    p = pairwise(c, ballots) if mode == "tideman-alternative" else None
    while len(active) > 1:
        if p is not None:
            smith = smith_set(active, p)
            if smith != active:
                trace.append({"active": active[:], "smith": smith})
                active = smith
                if len(active) == 1:
                    break
        first = first_counts(active, ballots)
        if mode in {"instant-runoff", "coombs", "tideman-alternative"}:
            majority = [x for x in active if first[x]*2 > total]
            if majority:
                trace.append({"active": active[:], "tally": first})
                return result(majority, trace)
        if mode == "coombs":
            tally = dict.fromkeys(active, 0)
            for b in ballots:
                last = next(x for x in reversed(b["ranking"]) if x in tally)
                tally[last] += b["count"]
            worst = best(tally)
        elif mode in {"nanson", "baldwin"}:
            tally = borda_counts(active, ballots)
            worst = best(tally, True)
        else:
            tally = first
            worst = best(tally, True)
        row = {"active": active[:], "tally": tally}
        if len(set(tally.values())) == 1 and (mode == "nanson" or len(active) == 2):
            trace.append(row)
            return result(active, trace)
        if mode == "nanson":
            eliminated = [x for x in active if tally[x]*len(active) <= sum(tally.values())]
        else:
            eliminated = [worst[-1]]
        row["eliminated"] = eliminated
        trace.append(row)
        active = [x for x in active if x not in eliminated]
    trace.append({"active": active[:]})
    return result(active, trace)

def count_nanson(c, ballots, options):
    return elimination(c, ballots, "nanson")

election = {'method': 'nanson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_nanson(election["candidates"], election["ballots"], election["options"])
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

function firstCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) tally[b.ranking!.find(c => active.includes(c))!] += b.count;
  return tally;
}

function bordaCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) {
    const order = b.ranking!.filter(c => active.includes(c));
    order.forEach((c, i) => { tally[c] += (active.length - 1 - i) * b.count; });
  }
  return tally;
}

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

function smith(active: string[], matrix: Pairwise): string[] {
  let smallest = active;
  for (const start of active) {
    const set = new Set([start]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const d of active) if (!set.has(d) && [...set].some(c => matrix[c][d] <= matrix[d][c])) { set.add(d); changed = true; }
    }
    if (set.size < smallest.length) smallest = active.filter(c => set.has(c));
  }
  return smallest;
}

function elimination(ctx: Context, mode: string): SimulationResult {
  let active = [...ctx.candidates];
  const trace: Trace = [];
  const matrix = mode === 'tideman-alternative' ? pairwise(ctx) : null;
  while (active.length > 1) {
    if (matrix) {
      const smithSet = smith(active, matrix);
      if (smithSet.length !== active.length) {
        trace.push({active: [...active], smith: smithSet});
        active = smithSet;
        if (active.length === 1) break;
      }
    }
    const first = firstCounts(ctx, active);
    if (['instant-runoff', 'coombs', 'tideman-alternative'].includes(mode)) {
      const majority = active.filter(c => first[c] * 2 > ctx.total);
      if (majority.length) { trace.push({active: [...active], tally: first}); return result(ctx, majority, trace); }
    }
    let tally = first;
    let worst: string[];
    if (mode === 'coombs') {
      tally = zeros(active);
      for (const b of ctx.ballots) tally[b.ranking!.filter(c => active.includes(c)).at(-1)!] += b.count;
      worst = best(active, tally);
    } else if (['nanson', 'baldwin'].includes(mode)) {
      tally = bordaCounts(ctx, active);
      worst = best(active, tally, true);
    } else worst = best(active, tally, true);
    const row: Record<string, unknown> = {active: [...active], tally};
    if (new Set(Object.values(tally)).size === 1 && (mode === 'nanson' || active.length === 2)) { trace.push(row); return result(ctx, active, trace); }
    const eliminated = mode === 'nanson'
      ? active.filter(c => tally[c] * active.length <= Object.values(tally).reduce((a, b) => a + b, 0))
      : [worst.at(-1)!];
    row.eliminated = eliminated;
    trace.push(row);
    active = active.filter(c => !eliminated.includes(c));
  }
  trace.push({active: [...active]});
  return result(ctx, active, trace);
}

export function countNanson(ctx: Context): SimulationResult { return elimination(ctx, 'nanson'); }

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

const election: Context = {
  "method": "nanson",
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
console.log(JSON.stringify(countNanson(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/nanson.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/nanson.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | A majority agreeing on a preferred group keeps the winner within that group. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | The standard rule excludes a candidate losing every pairwise comparison. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Smith set](/criteria.md#smith) | pass | The standard rule chooses only from the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Monotonicity](/criteria.md#monotonicity) | fail | Extra support can change a later contest or search score so that a previous winner loses. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | The usual rule is reported reversal symmetric, but consequential equal elimination totals and a fixed external priority must be treated explicitly. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | At most m rounds; O(bm²). [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Summability](/criteria.md#summability) | pass | O(m²) original pairwise counts suffice; two-round also needs O(m) first-choice totals. For Nanson and Baldwin, restricted Borda points equal the sum of pairwise support against remaining rivals. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |

## Cost and limits

At most m rounds; O(bm²).

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Iterative methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
