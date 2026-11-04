# Quadratic voting (credit budget)

A voter may cast multiple signed voice votes, paying the square of each amount from a fixed personal budget. Sum voice votes to select the winner.

**Ballot:** credits. **API identifier:** `quadratic`.

## Counting rule

1. For each ballot require integer voice amounts for all candidates.
2. Check that the sum of squared amounts is at most the declared budget.
3. Add signed voice votes per candidate and return the largest total.

**Variant used here:** Equal, nontransferable per-voter credit budget; credits fields contain voice votes v, whose cost is v². This is a teaching extension to multiple candidates, not the original binary money-purchase model.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "quadratic",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "credits": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "credits": {
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
  "method": "quadratic",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "tally": {
        "A": 20,
        "B": 32,
        "C": 19
      },
      "budget": 100
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Quadratic voting (credit budget) — complete algorithm">

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

def count_quadratic(c, ballots, options):
    # credits records signed voice votes; the budget charges their squares.
    tally = {x: sum(b["credits"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally, "budget": options["budget"]}])

election = {'method': 'quadratic', 'candidates': ['A', 'B', 'C'], 'ballots': [{'credits': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'credits': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'credits': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_quadratic(election["candidates"], election["ballots"], election["options"])
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

export function countQuadratic(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.credits![c] * b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally, budget: ctx.budget}]);
}

const election: Context = {
  "method": "quadratic",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "credits": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "credits": {
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
console.log(JSON.stringify(countQuadratic(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/quadratic.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/quadratic.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Rated majority](/criteria.md#majority-rated) | not-applicable | A voice-credit budget is not an independent bounded grade for each candidate; the cost constraint couples the amounts. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Weak Pareto](/criteria.md#weak-pareto) | conditional | If every submitted signed voice value for A exceeds B’s value, A’s sum exceeds B’s. Unexpressed preferences need not follow the constrained voice allocation. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Strong Pareto](/criteria.md#strong-pareto) | conditional | If A’s submitted voice value is at least B’s on every ballot and greater on one, A’s sum is greater. This is submitted-value dominance. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Monotonicity](/criteria.md#monotonicity) | conditional | Increasing only A’s voice amount increases A’s total when the changed ballot still satisfies its credit budget; spending more on A may otherwise require reducing other amounts. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Consistency / reinforcement](/criteria.md#consistency) | pass | For additive totals, positive winning margins in separate groups stay positive when the totals are added. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Participation](/criteria.md#participation) | conditional | Summing signed voices is additive, but strategic credit allocation and preference comparisons require a model beyond simple rankings. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm) tally and budget validation. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Summability](/criteria.md#summability) | pass | O(m) candidate totals are additive; random ballot also needs the electorate total. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Later no harm](/criteria.md#later-no-harm) | not-applicable | This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Later no help](/criteria.md#later-no-help) | not-applicable | This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |

## Cost and limits

O(bm) tally and budget validation.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Lalley and Weyl: Quadratic Voting](https://bfi.uchicago.edu/working-paper/quadratic-voting/)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
