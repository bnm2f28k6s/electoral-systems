# Schulze STV

Compare committees that differ by one candidate using balanced voter support. Strongest paths through the committee graph resolve indirect comparisons.

**Ballot:** ranking. **API identifier:** `schulze-stv` at `/multi/simulate`.

## Counting rule

1. Enumerate all size-k committees, linking those that differ by one candidate.
2. For a link X→Y, let b be the candidate in Y but not X. Balance ballot weight among members of X ranked above b to maximize the minimum support of a member of X.
3. Compute maximum-strength bottleneck paths between committees. A committee wins when no reverse strongest path is strictly stronger.
4. Compute the ordinary single-winner Schulze strict order as well. Among the stage-two committee winners, disqualify B if another stage-two winner A contains at least one candidate in A\B who is strictly above every candidate in B\A in that order.

**Implemented variant:** Strict rankings and the voter-management linear program from Schulze’s specification. An exact small solver uses the equivalent Hall-style subset bound for common support, strongest paths on raw directed links, and the specification’s final single-winner-Schulze disqualification stage.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "schulze-stv",
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

**The selected committee is A and C.** Compare A–C with A–B. Against outsider B, four voters can support C and nine can support A; all ten can support at least one of A or C. The largest equally shared support is min(9, 4, 10/2) = 4. In the reverse direction, only the six majority voters can support A or B above C, so the equal support is 6/2 = 3. The full strongest-path comparison selects A–C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "schulze-stv",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "committees": [
        [
          "A",
          "B"
        ],
        [
          "A",
          "C"
        ],
        [
          "A",
          "D"
        ],
        [
          "B",
          "C"
        ],
        [
          "B",
          "D"
        ],
        [
          "C",
          "D"
        ]
      ],
      "links": [
        [
          0.0,
          3.0,
          3.0,
          3.0,
          3.0,
          0.0
        ],
        [
          4.0,
          0.0,
          4.5,
          4.0,
          0.0,
          4.5
        ],
        [
          4.0,
          1.0,
          0.0,
          0.0,
          4.0,
          1.0
        ],
        [
          1.0,
          1.0,
          0.0,
          0.0,
          4.5,
          4.5
        ],
        [
          1.0,
          0.0,
          1.0,
          1.0,
          0.0,
          1.0
        ],
        [
          0.0,
          2.0,
          2.0,
          2.0,
          2.0,
          0.0
        ]
      ],
      "strongestPaths": [
        [
          0.0,
          3.0,
          3.0,
          3.0,
          3.0,
          3.0
        ],
        [
          4.0,
          0.0,
          4.5,
          4.0,
          4.0,
          4.5
        ],
        [
          4.0,
          3.0,
          0.0,
          3.0,
          4.0,
          3.0
        ],
        [
          2.0,
          2.0,
          2.0,
          0.0,
          4.5,
          4.5
        ],
        [
          1.0,
          1.0,
          1.0,
          1.0,
          0.0,
          1.0
        ],
        [
          2.0,
          2.0,
          2.0,
          2.0,
          2.0,
          0.0
        ]
      ],
      "stageTwoCommittees": [
        [
          "A",
          "C"
        ]
      ],
      "singleWinnerPaths": {
        "A": {
          "A": 0,
          "B": 9,
          "C": 6,
          "D": 6
        },
        "B": {
          "A": 4,
          "B": 0,
          "C": 6,
          "D": 6
        },
        "C": {
          "A": 4,
          "B": 4,
          "C": 0,
          "D": 9
        },
        "D": {
          "A": 4,
          "B": 4,
          "C": 4,
          "D": 0
        }
      },
      "tiedCommittees": [
        [
          "A",
          "C"
        ]
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. These programs demonstrate counting valid profiles. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits.

<CodeSelect title="Schulze STV — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def pairwise(c, ballots):
    matrix = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                matrix[x][y] += b["count"]
    return matrix

def schulze_strength(committee, outsider, ballots):
    # Weighted Hall inequalities for assigning equal support to each member:
    # t*|S| <= weight of voters preferring some member of S to the outsider.
    strength = None
    for size in range(1, len(committee)+1):
        for subset in itertools.combinations(committee, size):
            support = sum(b["count"] for b in ballots if any(b["ranking"].index(x) < b["ranking"].index(outsider) for x in subset))
            value = Fraction(support, size)
            strength = value if strength is None else min(strength, value)
    return strength

def count_schulze_stv(c, ballots, seats, options):
    committees = list(itertools.combinations(c, seats))
    n = len(committees)
    links = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for i, first in enumerate(committees):
        for j, second in enumerate(committees):
            outsiders = [x for x in second if x not in first]
            if len(outsiders) == 1:
                links[i][j] = schulze_strength(first, outsiders[0], ballots)
    paths = [row[:] for row in links]
    for middle in range(n):
        for start in range(n):
            for end in range(n):
                if len({middle, start, end}) == 3:
                    paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
    stage_two = [list(committees[i]) for i in range(n) if all(paths[i][j] >= paths[j][i] for j in range(n))]
    # The published rule has a third stage: a committee can disqualify another
    # tied committee using the strict single-winner Schulze relation.
    single = pairwise(c, ballots)
    for middle in c:
        for start in c:
            for end in c:
                if len({middle, start, end}) == 3:
                    single[start][end] = max(single[start][end], min(single[start][middle], single[middle][end]))
    tied = [second for second in stage_two if not any(
        any(all(single[a][b] > single[b][a] for b in second if b not in first)
            for a in first if a not in second)
        for first in stage_two if first != second)]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [list(x) for x in committees], "links": [[float(v) for v in row] for row in links], "strongestPaths": [[float(v) for v in row] for row in paths], "stageTwoCommittees": stage_two, "singleWinnerPaths": single, "tiedCommittees": tied}]}

election = {'method': 'schulze-stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_schulze_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
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

function integer(value: unknown, low: number, high: number, name: string): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < low || value > high)
    throw new ElectionError(`${name} must be an integer from ${low} to ${high}`);
  return value;
}

function gcd(a: bigint, b: bigint): bigint {while (b) {const next = b; b = a % b; a = next;} return a < 0n ? -a : a;}

function fraction(n: number | bigint, d: number | bigint = 1): Fraction {
  let a = BigInt(n), b = BigInt(d); if (b < 0n) {a = -a; b = -b;} const g = gcd(a, b); return [a / g, b / g];
}

function compare(a: Fraction, b: Fraction): number {const d = a[0] * b[1] - b[0] * a[1]; return d < 0n ? -1 : d > 0n ? 1 : 0;}
/** Round an exact rational to a JSON-display number without BigInt overflow.
 * Election decisions use compare(), never this floating-point conversion.
 */

export function asNumber(a: Fraction): number {
  let numerator = a[0], denominator = a[1];
  if (denominator === 0n) throw new RangeError('A rational denominator cannot be zero');
  const negative = (numerator < 0n) !== (denominator < 0n);
  if (numerator < 0n) numerator = -numerator;
  if (denominator < 0n) denominator = -denominator;
  if (numerator === 0n) return 0;
  // Determine the binary exponent while retaining all integer precision.
  let exponent = numerator.toString(2).length - denominator.toString(2).length;
  if (exponent >= 0 ? numerator < (denominator << BigInt(exponent)) : (numerator << BigInt(-exponent)) < denominator) exponent--;
  if (exponent > 1023) return negative ? -Infinity : Infinity;
  // Normal doubles have 53 significant bits; subnormals use units of 2^-1074.
  const shift = exponent < -1022 ? 1074 : 52 - exponent;
  const top = shift >= 0 ? numerator << BigInt(shift) : numerator;
  const bottom = shift >= 0 ? denominator : denominator << BigInt(-shift);
  let significant = top / bottom;
  const remainder = top % bottom;
  // IEEE-754 round-to-nearest, choosing the even significand at an exact tie.
  if (2n * remainder > bottom || (2n * remainder === bottom && significant % 2n === 1n)) significant++;
  const value = Number(significant) * (exponent < -1022 ? Number.MIN_VALUE : 2 ** (exponent - 52));
  return negative ? -value : value;
}

function zeros(candidates: string[]): Tally {return Object.fromEntries(candidates.map(c => [c, 0]));}

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function pairwise(ctx: Context): Matrix {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const ballot of ctx.ballots) {
    const ranking = ballot.ranking!;
    ranking.forEach((a, index) => {for (const b of ranking.slice(index + 1)) matrix[a][b] += ballot.count;});
  }
  return matrix;
}

function* combinations<T>(items: T[], k: number, start = 0, prefix: T[] = []): Generator<T[]> {
  if (!k) {yield prefix; return;}
  for (let i = start; i <= items.length - k; i++) yield* combinations(items, k - 1, i + 1, [...prefix, items[i]]);
}

function schulzeStrength(ctx: Context, committee: string[], outsider: string): Fraction {
  let strength: Fraction | null = null;
  for (let size = 1; size <= committee.length; size++) for (const subset of combinations(committee, size)) {
    const support = ctx.ballots.reduce((sum, b) => sum + (subset.some(c => b.ranking!.indexOf(c) < b.ranking!.indexOf(outsider)) ? b.count : 0), 0);
    const value = fraction(support, size);
    if (strength === null || compare(value, strength) < 0) strength = value;
  }
  return strength!;
}

export function countSchulzeStv(ctx: Context): SimulationResult {
  const committees = [...combinations(ctx.candidates, ctx.seats)], n = committees.length;
  const links = committees.map(() => committees.map(() => fraction(0)));
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const outsiders = committees[j].filter(c => !committees[i].includes(c));
    if (outsiders.length === 1) links[i][j] = schulzeStrength(ctx, committees[i], outsiders[0]);
  }
  const paths = links.map(row => [...row]);
  for (let middle = 0; middle < n; middle++) for (let start = 0; start < n; start++) for (let end = 0; end < n; end++) {
    if (new Set([middle, start, end]).size === 3) {
      const strength = compare(paths[start][middle], paths[middle][end]) < 0 ? paths[start][middle] : paths[middle][end];
      if (compare(strength, paths[start][end]) > 0) paths[start][end] = strength;
    }
  }
  const stageTwoCommittees = committees.filter((_, i) => paths[i].every((strength, j) => compare(strength, paths[j][i]) >= 0));
  const singleWinnerPaths = pairwise(ctx);
  for (const middle of ctx.candidates) for (const start of ctx.candidates) for (const end of ctx.candidates) {
    if (new Set([middle, start, end]).size === 3) singleWinnerPaths[start][end] = Math.max(singleWinnerPaths[start][end], Math.min(singleWinnerPaths[start][middle], singleWinnerPaths[middle][end]));
  }
  const tied = stageTwoCommittees.filter(second => !stageTwoCommittees.some(first => first !== second && first.filter(c => !second.includes(c)).some(a => second.filter(c => !first.includes(c)).every(b => singleWinnerPaths[a][b] > singleWinnerPaths[b][a]))));
  return result(ctx, tied[0], tied.length > 1, [{committees, links: links.map(row => row.map(asNumber)), strongestPaths: paths.map(row => row.map(asNumber)), stageTwoCommittees, singleWinnerPaths, tiedCommittees: tied}]);
}

const election: Context = {
  "method": "schulze-stv",
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
console.log(JSON.stringify(countSchulzeStv(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/python/schulze-stv.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-multi-winner-examples/examples/multi/typescript/schulze-stv.ts) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | conditional | The specification studies proportionality for its exact voter-management committee graph. Applying the theorem requires the same quota/support and tie assumptions; the bounded solver is not evidence from simulation alone. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | conditional | Schulze’s voter-management construction is designed with monotonicity guarantees. The theorem’s specified ordering and tie conventions must be matched before asserting it for an arbitrary fixed-priority selector. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | conditional | The strongest-path construction operates over committees and excludes committees beaten outside the comparison graph’s Smith set. This is the rule-specific committee Smith statement, not a claim that every individual belongs to a single-winner Smith set. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | Committee comparisons or strongest paths are not additive final objectives. No exact-variant proof or direct counterexample is supplied here; Condorcet completion alone is not a consistency proof. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | The stronger unanimous top-k-set guarantee holds for the full procedure, including its final single-winner-Schulze disqualification stage. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | pass | A unanimous top-k set has zero-strength incoming neighboring links, so it survives the committee strongest-path stage. The final ordinary-Schulze disqualification then removes each other surviving committee: every omitted top-set candidate is strictly above every introduced outsider. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | fail | The self-contained exact implementation enumerates candidate subsets, committees or committee pairs. Its documented small input cap controls runtime but is not a polynomial-time algorithm for unbounded candidate counts. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

Exponential committee and nonempty-subset enumeration plus O(C³) strongest paths and polynomial final disqualification checks, C=binomial(m,k).

Exact committee comparisons are limited to 6 candidates and 100 ballot groups, in addition to the shared API limits. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Schulze: Schulze STV specification, voter management](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
