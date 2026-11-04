# Random ballot (random dictatorship)

Choose a voter uniformly at random and elect that voter’s first choice. A ballot group with count 5 represents five opportunities, not one.

**Ballot:** choice or ranking. **API identifier:** `random-ballot`.

## Counting rule

1. Count first choices, weighted by voter counts.
2. Divide each first-choice total by the total electorate to form a lottery.
3. Use the supplied seed to sample one winner from that lottery.

**Variant used here:** The reported probabilities define the rule. A deterministic pseudorandom seed makes a demonstration reproducible; it is not election-grade randomness.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "random-ballot",
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

The sampled winner is **A** with seed 1. The distribution in the response describes the rule; the sampled name is one reproducible draw. The trace records intermediate totals, eliminations, comparisons, or the lottery used by this rule.

```json
{
  "method": "random-ballot",
  "winners": [
    "A"
  ],
  "tie": false,
  "trace": [
    {
      "tally": {
        "A": 4,
        "B": 3,
        "C": 2
      },
      "seed": 1
    }
  ],
  "lottery": [
    {
      "candidate": "A",
      "probability": 0.4444444444444444
    },
    {
      "candidate": "B",
      "probability": 0.3333333333333333
    },
    {
      "candidate": "C",
      "probability": 0.2222222222222222
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Random ballot (random dictatorship) — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def first_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        choice = b.get("choice") or next(x for x in b["ranking"] if x in active)
        tally[choice] += b["count"]
    return tally

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def count_random_ballot(c, ballots, options):
    tally = first_counts(c, ballots)
    total = sum(tally.values())
    lottery = [{"candidate": x, "probability": tally[x]/total} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"tally": tally, "seed": options["seed"]}], lottery=lottery)

election = {'method': 'random-ballot', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_random_ballot(election["candidates"], election["ballots"], election["options"])
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

function randomUnit(seed: number): number { return ((Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296; }

function sample(probabilities: number[], seed: number): number {
  const draw = randomUnit(seed);
  let cumulative = 0;
  for (let i = 0; i < probabilities.length; i++) { cumulative += probabilities[i]; if (draw < cumulative) return i; }
  return probabilities.length - 1;
}

export function countRandomBallot(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) tally[b.choice ?? b.ranking![0]] += b.count;
  const probabilities = ctx.candidates.map(c => tally[c] / ctx.total);
  const chosen = sample(probabilities, ctx.seed);
  return result(ctx, [ctx.candidates[chosen]], [{tally, seed: ctx.seed}], probabilities);
}

const election: Context = {
  "method": "random-ballot",
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
console.log(JSON.stringify(countRandomBallot(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/random-ballot.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/random-ballot.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Rated majority](/criteria.md#majority-rated) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Majority loser](/criteria.md#majority-loser) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. Unanimous strict preference prevents the dominated candidate winning on the stated ballot domain. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. On complete strict rankings, weak and strong Pareto have the same test. Unanimous strict preference prevents the dominated candidate winning on the stated ballot domain. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Smith set](/criteria.md#smith) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. The rule can elect outside the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing a Smith outsider who has some first-choice support redistributes that support. The resulting probabilities of Smith candidates can change, despite unchanged rankings among them. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | pass | With sincere complete strict rankings, a unanimously dominated candidate is never first. Removing that candidate leaves all first-choice probabilities unchanged. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | conditional | If the chosen ballot keeps the same first choice after a nonwinning option is removed, that ballot’s winner is unchanged. General distributional candidate deletion requires a different definition. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | conditional | Assess the lottery distribution, not the winner sampled with a fixed seed. Requires an explicit ballot-domain, tie, or lottery interpretation; see the criterion guide. This is not an unconditional guarantee for the simulation. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Assess the lottery distribution, not the winner sampled with a fixed seed. Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | conditional | Population consistency applies to a common probability distribution: combining electorates with the same first-choice proportions preserves it. Equality of two sampled winners is not enough. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Participation](/criteria.md#participation) | conditional | Truthful participation improves the random-dictatorship distribution in the stochastic-dominance sense. This does not promise that one seeded sample improves. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | A candidate can have positive probability before and after reversal. If the original distribution is concentrated entirely on one candidate, reversal excludes that candidate. A lottery analogue must specify which statement it requires. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Assess the lottery distribution, not the winner sampled with a fixed seed. Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(b + m) tallying and sampling. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Resolvability](/criteria.md#resolvability) | not-applicable | Randomness is part of the outcome rule, not merely a device for resolving exact counting ties. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Summability](/criteria.md#summability) | pass | O(m) candidate totals are additive; random ballot also needs the electorate total. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | pass | Lower preferences are not used against higher preferences in the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Later no help](/criteria.md#later-no-help) | pass | Adding a lower preference cannot improve an already higher candidate’s outcome under the standard interpretation. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | pass | A voter can obtain an optimal outcome without putting a less-preferred candidate strictly above a favorite. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |

## Cost and limits

O(b + m) tallying and sampling.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Probabilistic methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
