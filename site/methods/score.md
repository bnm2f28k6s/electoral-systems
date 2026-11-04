# Score voting (range voting)

Voters grade every candidate on a common bounded scale. The largest sum wins.

**Ballot:** scores. **API identifier:** `score`.

## Counting rule

1. Require an integer grade from zero to maxScore for every candidate.
2. Multiply each grade by its ballot count and add each candidate’s total.
3. Return the largest total; all candidates have the same number of submitted grades, so means give the same order.

**Variant used here:** Complete ratings, summed without normalization or per-ballot rescaling.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "score",
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
  "method": "score",
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
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Score voting (range voting) — complete algorithm">

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

def count_score(c, ballots, options):
    tally = {x: sum(b["scores"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally}])

election = {'method': 'score', 'candidates': ['A', 'B', 'C'], 'ballots': [{'scores': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'scores': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'scores': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_score(election["candidates"], election["ballots"], election["options"])
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

export function countScore(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.scores![c] * b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally}]);
}

const election: Context = {
  "method": "score",
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
console.log(JSON.stringify(countScore(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/score.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/score.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Rated majority](/criteria.md#majority-rated) | fail | A majority can uniquely give A the maximum yet give B almost as much; the minority can then make B’s summed score larger. For example 51×(A5,B4),49×(A0,B5). [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | Unanimous strict preference prevents the dominated candidate winning on the stated ballot domain. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | For submitted grades, A at least B on every ballot and strictly above B on one gives A a strictly larger sum. Hidden preferences collapsed into equal grades are a different claim. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Smith independence](/criteria.md#smith-iia) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | conditional | With unchanged absolute submitted grades, removing another candidate leaves each retained candidate’s grade distribution unchanged. Regrading after candidate entry or inferring hidden rankings is a different model. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | conditional | When the social ordering is formed from unchanged absolute submitted grades, deleting any candidate leaves retained grade comparisons unchanged. The API itself reports only winners. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Independence of clones](/criteria.md#clone-independence) | conditional | Identically graded copies do not change existing totals or distributions. Ordinal clones with different grades need not behave as identical copies. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Consistency / reinforcement](/criteria.md#consistency) | pass | For additive totals, positive winning margins in separate groups stay positive when the totals are added. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Participation](/criteria.md#participation) | conditional | For additive grades, an honest nonincreasing grading cannot worsen a resolute outcome when ties are consistently resolved. Hidden utilities and set-valued outcomes need separate definitions. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | pass | Reversing every strict preference excludes a former unique winner under the standard interpretation. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm) tally work. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Summability](/criteria.md#summability) | pass | O(m) candidate totals are additive; random ballot also needs the electorate total. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [Later no help](/criteria.md#later-no-help) | pass | Adding a lower preference cannot improve an already higher candidate’s outcome under the standard interpretation. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | pass | A voter can obtain an optimal outcome without putting a less-preferred candidate strictly above a favorite. [Source](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf). |

## Cost and limits

O(bm) tally work.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Handbook of Computational Social Choice](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
