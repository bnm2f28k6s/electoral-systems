# Majority judgment

Use each candidate’s middle grade rather than their average. Break equal middle grades by repeatedly removing one occurrence of that grade.

**Ballot:** scores. **API identifier:** `majority-judgment`.

## Counting rule

1. Build a weighted grade distribution for each candidate.
2. Compare lower medians: for an even number of grades, use the lower of the two central grades.
3. For tied leaders, remove one median grade each and compare again until they separate or all grades are exhausted.

**Variant used here:** Integer ordered grades, lower median and repeated median deletion; not simply highest median with arbitrary tie-breaking.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "majority-judgment",
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
  "method": "majority-judgment",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "majorityGrades": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "histograms": {
        "A": [
          5,
          0,
          0,
          0,
          0,
          4
        ],
        "B": [
          0,
          0,
          0,
          4,
          5,
          0
        ],
        "C": [
          4,
          0,
          0,
          3,
          0,
          2
        ]
      }
    },
    {
      "medianGradesRemoved": 0,
      "remaining": [
        "B"
      ]
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Majority judgment — complete algorithm">

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

def count_majority_judgment(c, ballots, options):
    histograms = {x: [sum(b["count"] for b in ballots if b["scores"][x] == grade) for grade in range(options["maxScore"]+1)] for x in c}
    def median(histogram):
        position = (sum(histogram)-1)//2
        cumulative = 0
        for grade, count in enumerate(histogram):
            cumulative += count
            if cumulative > position:
                return grade
        return -1
    initial = {x: median(histograms[x]) for x in c}
    trace = [{"majorityGrades": initial, "histograms": {x: h[:] for x, h in histograms.items()}}]
    active = best(initial)
    removed = 0
    while len(active) > 1 and sum(histograms[active[0]]) > 0:
        # One lower median removed per tied candidate per iteration.
        # Equal histograms can never separate; stop without expanding voters.
        if all(histograms[x] == histograms[active[0]] for x in active):
            break
        batch = min(min(sum(histograms[x])-1-2*sum(histograms[x][:median(histograms[x])]),
                            2*sum(histograms[x][:median(histograms[x])])+2*histograms[x][median(histograms[x])]-sum(histograms[x]))+1 for x in active)
        for x in active:
            histograms[x][median(histograms[x])] -= batch
        removed += batch
        grades = {x: median(histograms[x]) for x in active}
        active = best(grades)
    trace.append({"medianGradesRemoved": removed, "remaining": active})
    return result(active, trace)

election = {'method': 'majority-judgment', 'candidates': ['A', 'B', 'C'], 'ballots': [{'scores': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'scores': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'scores': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_majority_judgment(election["candidates"], election["ballots"], election["options"])
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

function median(histogram: number[]): number {
  const position = Math.floor((histogram.reduce((a, b) => a + b, 0) - 1) / 2);
  let cumulative = 0;
  for (let grade = 0; grade < histogram.length; grade++) {
    cumulative += histogram[grade];
    if (cumulative > position) return grade;
  }
  return -1;
}

export function countMajorityJudgment(ctx: Context): SimulationResult {
  const histograms = Object.fromEntries(ctx.candidates.map(c => [c, Array(ctx.maxScore + 1).fill(0) as number[]]));
  for (const b of ctx.ballots) for (const c of ctx.candidates) histograms[c][b.scores![c]] += b.count;
  const initial = Object.fromEntries(ctx.candidates.map(c => [c, median(histograms[c])]));
  const trace: Trace = [{majorityGrades: initial, histograms: Object.fromEntries(ctx.candidates.map(c => [c, [...histograms[c]]]))}];
  let active = best(ctx.candidates, initial);
  let removed = 0;
  while (active.length > 1 && histograms[active[0]].reduce((a, b) => a + b, 0) > 0) {
    if (active.every(c => histograms[c].every((v, i) => v === histograms[active[0]][i]))) break;
    // Batch exactly the removals until at least one tied candidate's median changes.
    const batch = Math.min(...active.map(c => {
      const h = histograms[c], grade = median(h);
      const n = h.reduce((a, b) => a + b, 0);
      const below = h.slice(0, grade).reduce((a, b) => a + b, 0);
      return Math.min(n - 1 - 2 * below, 2 * below + 2 * h[grade] - n) + 1;
    }));
    for (const c of active) histograms[c][median(histograms[c])] -= batch;
    removed += batch;
    const grades = Object.fromEntries(active.map(c => [c, median(histograms[c])]));
    active = best(active, grades);
  }
  trace.push({medianGradesRemoved: removed, remaining: active});
  return result(ctx, active, trace);
}

const election: Context = {
  "method": "majority-judgment",
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
console.log(JSON.stringify(countMajorityJudgment(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/majority-judgment.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/majority-judgment.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Rated majority](/criteria.md#majority-rated) | pass | If more than half grade only A at the maximum, A’s lower median is that maximum and every rival’s median is smaller. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | Unanimous strict preference prevents the dominated candidate winning on the stated ballot domain. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | Submitted weak grade dominance implies every sorted A grade is at least the corresponding B grade, with some strict inequality. The common median-deletion index order must eventually favor A. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Smith independence](/criteria.md#smith-iia) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | conditional | When the social ordering is formed from unchanged absolute submitted grades, deleting any candidate leaves retained grade comparisons unchanged. The API itself reports only winners. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Independence of clones](/criteria.md#clone-independence) | conditional | Identically graded copies do not change existing totals or distributions. Ordinal clones with different grades need not behave as identical copies. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Participation](/criteria.md#participation) | fail | Median comparisons can change when an honest voter joins, giving that voter a worse outcome than abstention. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | Requires an explicit ballot-domain, tie, or lottery interpretation; see the criterion guide. This is not an unconditional guarantee for the simulation. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | Histogram construction O(bmg), then at most N median deletions costing O(mg) each; N is represented voters, g is grade count. Batching often skips many equal-grade deletions. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Resolvability](/criteria.md#resolvability) | unverified | No asymptotic tie-frequency theorem is asserted for this exact variant. A fixed priority or seed makes execution repeatable but does not prove resolvability. [Source](https://arxiv.org/abs/1804.02973). |
| [Summability](/criteria.md#summability) | pass | O(mg) grade histograms are additive for m candidates and g permitted grades; do not add precinct medians. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [Later no help](/criteria.md#later-no-help) | pass | Adding a lower preference cannot improve an already higher candidate’s outcome under the standard interpretation. [Source](https://doi.org/10.1073/pnas.0702634104). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | pass | A voter can obtain an optimal outcome without putting a less-preferred candidate strictly above a favorite. [Source](https://doi.org/10.1073/pnas.0702634104). |

## Cost and limits

Histogram construction O(bmg), then at most N median deletions costing O(mg) each; N is represented voters, g is grade count. Batching often skips many equal-grade deletions.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Balinski and Laraki: A theory of measuring, electing, and ranking](https://doi.org/10.1073/pnas.0702634104)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
