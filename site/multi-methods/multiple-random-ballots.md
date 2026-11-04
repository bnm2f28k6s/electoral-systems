# Multiple random ballots

For each seat, sample a voter and elect that ballot’s highest-ranked candidate not already elected. Repeating the draw can represent different voter groups without guaranteeing proportionality.

**Ballot:** ranking. **API identifier:** `multiple-random-ballots` at `/multi/simulate`.

## Counting rule

1. For each seat, count the highest remaining candidate on every ballot.
2. Draw a candidate with probability equal to its current first-choice share; this is equivalent to an independent uniformly random voter draw.
3. Remove the elected candidate and repeat, keeping all original ballots available for subsequent draws.

**Implemented variant:** Explicit repeated-ballot teaching variant: voters are sampled independently with replacement, candidates cannot be elected twice, and rankings transfer past elected candidates. The comparison’s broad label does not uniquely specify every multi-seat random-ballot variant.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "multiple-random-ballots",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C",
        "D"
      ],
      "count": 6
    },
    {
      "ranking": [
        "C",
        "D",
        "A",
        "B"
      ],
      "count": 3
    },
    {
      "ranking": [
        "D",
        "C",
        "B",
        "A"
      ],
      "count": 1
    }
  ],
  "options": {
    "maxScore": 5,
    "budget": 100,
    "limit": 1,
    "seed": 1
  }
}
```

**The selected committee is A and B.** With seed one, both independent ballot draws select a ballot from the six-voter A–B group. The first draw elects A; the next elects that ballot's highest remaining candidate, B. Other seeds can choose different committees.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "multiple-random-ballots",
  "seats": 2,
  "winners": [
    "A",
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "round": 1,
      "tally": {
        "A": 6,
        "B": 0,
        "C": 3,
        "D": 1
      },
      "probabilities": {
        "A": 0.6,
        "B": 0.0,
        "C": 0.3,
        "D": 0.1
      },
      "selected": "A",
      "state": 1015568748
    },
    {
      "round": 2,
      "tally": {
        "B": 6,
        "C": 3,
        "D": 1
      },
      "probabilities": {
        "B": 0.6,
        "C": 0.3,
        "D": 0.1
      },
      "selected": "B",
      "state": 1586005467
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Multiple random ballots — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def number_map(tally):
    return {x: float(value) if isinstance(value, Fraction) else value for x, value in tally.items()}

def draw(c, tally, seed):
    state = (1664525*seed+1013904223) % 2**32
    total = sum(tally.values())
    threshold, cumulative = Fraction(state, 2**32), Fraction(0)
    probabilities = {x: Fraction(tally[x], total) for x in c}
    for x in c:
        cumulative += probabilities[x]
        if threshold < cumulative:
            return x, state, number_map(probabilities)
    return c[-1], state, number_map(probabilities)

def count_multiple_random_ballots(c, ballots, seats, options):
    active, elected, trace, seed = c[:], [], [], options["seed"]
    for step in range(seats):
        tally = dict.fromkeys(active, 0)
        for b in ballots:
            tally[next(x for x in b["ranking"] if x in active)] += b["count"]
        winner, seed, probabilities = draw(active, tally, seed)
        elected.append(winner)
        active.remove(winner)
        trace.append({"round": step+1, "tally": tally, "probabilities": probabilities, "selected": winner, "state": seed})
    return {"winners": ordered(c, elected), "tie": False, "trace": trace}

election = {'method': 'multiple-random-ballots', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_multiple_random_ballots(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
```

```typescript
// Node 22.18+. Save as example.ts and run: node example.ts
// Complete count for valid input. The API performs full validation.
export const METHODS = [
  'approval', 'proportional-approval', 'sequential-proportional-approval',
  'reweighted-range', 'stv', 'cpo-stv', 'schulze-stv', 'phragmen', 'k-borda',
  'bloc', 'quota-borda', 'expanding-approvals', 'minimax',
  'minimax-external-opposition', 'single-non-transferable', 'limited-vote',
  'cumulative', 'sortition', 'multiple-random-ballots',
] as const;
export type Method = typeof METHODS[number];
export type Ballot = { count?: number; ranking?: string[]; approvals?: string[];
  choice?: string; scores?: Record<string, number>; votes?: Record<string, number> };
export type ElectionRequest = { method: Method; candidates: string[]; seats: number;
  ballots: Ballot[]; options?: {maxScore?: number; budget?: number; limit?: number; seed?: number} };
export type Trace = Record<string, unknown>[];
export type SimulationResult = {method: Method; seats: number; winners: string[]; tie: boolean; trace: Trace};
type Context = {method: Method; candidates: string[]; seats: number; ballots: (Ballot & {count: number})[];
  maxScore: number; budget: number; limit: number; seed: number; total: number};
type Tally = Record<string, number>;
type Matrix = Record<string, Tally>;
type Fraction = [bigint, bigint];
export class ElectionError extends Error {
  status: number;
  constructor(message: string, status = 400) {super(message); this.name = 'ElectionError'; this.status = status;}
}

function gcd(a: bigint, b: bigint): bigint {while (b) {const next = b; b = a % b; a = next;} return a < 0n ? -a : a;}

function fraction(n: number | bigint, d: number | bigint = 1): Fraction {
  let a = BigInt(n), b = BigInt(d); if (b < 0n) {a = -a; b = -b;} const g = gcd(a, b); return [a / g, b / g];
}

function add(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);}

function compare(a: Fraction, b: Fraction): number {const d = a[0] * b[1] - b[0] * a[1]; return d < 0n ? -1 : d > 0n ? 1 : 0;}
/** Round an exact rational to a JSON-display number without BigInt overflow.
 * Election decisions use compare(), never this floating-point conversion.
 */

function zeros(candidates: string[]): Tally {return Object.fromEntries(candidates.map(c => [c, 0]));}

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function draw(candidates: string[], tally: Tally, seed: number): {winner: string; state: number; probabilities: Tally} {
  const state = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  const total = candidates.reduce((sum, c) => sum + tally[c], 0);
  const threshold = fraction(state, 4294967296);
  let cumulative = fraction(0), winner = candidates[candidates.length - 1], chosen = false;
  const probabilities = Object.fromEntries(candidates.map(c => [c, tally[c] / total]));
  for (const c of candidates) {
    cumulative = add(cumulative, fraction(tally[c], total));
    if (!chosen && compare(threshold, cumulative) < 0) {winner = c; chosen = true;}
  }
  return {winner, state, probabilities};
}

export function countMultipleRandomBallots(ctx: Context): SimulationResult {
  const active = [...ctx.candidates], elected: string[] = [], trace: Trace = [];
  let seed = ctx.seed;
  for (let step = 0; step < ctx.seats; step++) {
    const tally = zeros(active);
    for (const b of ctx.ballots) tally[b.ranking!.find(c => active.includes(c))!] += b.count;
    const {winner, state, probabilities} = draw(active, tally, seed);
    seed = state; elected.push(winner); active.splice(active.indexOf(winner), 1);
    trace.push({round: step + 1, tally, probabilities, selected: winner, state});
  }
  return result(ctx, elected, false, trace);
}

const election: Context = {
  "method": "multiple-random-ballots",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "ranking": [
        "A",
        "B",
        "C",
        "D"
      ],
      "count": 6
    },
    {
      "ranking": [
        "C",
        "D",
        "A",
        "B"
      ],
      "count": 3
    },
    {
      "ranking": [
        "D",
        "C",
        "B",
        "A"
      ],
      "count": 1
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "limit": 1,
  "seed": 1,
  "total": 10
};
console.log(JSON.stringify(countMultipleRandomBallots(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/multiple-random-ballots.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/multiple-random-ballots.ts) program.

## Simulate this committee through HTTP

Start `python3 python/server.py` from the repository root. Save the request above as `committee.json`, then run:

```sh
curl --fail-with-body http://127.0.0.1:8000/multi/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @committee.json
```

The server executes this Python counting function and returns the response shown above. The [committee API guide](/multi-api.md) explains the response fields and errors. The [single-winner endpoint](/api-design.md) remains available separately.

## Criteria and assumptions

Read the [multi-winner criteria guide](/multi-criteria.md) before comparing labels. A criterion concerns whole classes of elections, not just this worked count. **Conditional** requires the stated domain or tie assumptions. **Unverified** records an unresolved assessment for the exact variant, rather than filling an empty source cell with a guarantee. Several committee criteria depend on how a voter compares groups of candidates; those assumptions are part of the definition.

| Criterion | Assessment | Explanation and source |
| --- | --- | --- |
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | fail | A small cohesive group can be missed in every finite independent voter draw with positive probability; representing groups in expectation does not guarantee PSC in each committee. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | fail | Even a candidate ranked first by N/k voters has a positive probability of being missed in a finite sequence of draws. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | conditional | For the distribution, couple the runs using the same sequence of sampled voters: raising candidate A can only elect A earlier or leave each earlier choice unchanged until A is elected. Candidate inclusion probability therefore cannot fall. A fixed seed sampling aggregate candidate shares is not that coupling and is not the criterion. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | pass | Under the ordinal candidate-replacement test, if every voter ranks A above B, no draw can select B while A remains unelected. Every positive-probability committee containing B therefore also contains A. This proof is for the explicit repeated highest-remaining variant, not every rule sharing the broad random-ballot label. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | pass | Under the ordinal candidate-replacement test, if every voter ranks A above B, no draw can select B while A remains unelected. Every positive-probability committee containing B therefore also contains A. This proof is for the explicit repeated highest-remaining variant, not every rule sharing the broad random-ballot label. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | conditional | With the same seed and fixed candidate and ballot order, the size-(k+1) run extends the size-k draw sequence, so sampled committees are nested. A distributional axiom comparing all co-winning outcomes needs its own interpretation. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | The distribution mixes conditional voter draws after previous selections. Agreement of one seeded sample is not agreement of the lottery; no correspondence-consistency theorem is claimed for this explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | pass | A uniquely first-ranked candidate on every ballot is chosen on the first draw. Adding that candidate and an extra seat consumes one draw then reproduces the original conditional lottery distribution for the other seats; compare distributions rather than identical seed offsets. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | The stronger unanimous top-k-set guarantee holds for this particular repeated-first-remaining variant. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | pass | If all voters put the same k-set above every outsider, each draw chooses an unelected member of that set until exactly that set has filled all k seats. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(kbm) for repeated first-remaining scans.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Random dictatorship: the single-draw primitive](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
