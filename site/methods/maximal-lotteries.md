# Maximal lotteries

Turn majority margins into a zero-sum game. Choose probabilities that cannot be beaten in expected pairwise margin by any rival lottery.

**Ballot:** ranking. **API identifier:** `maximal-lotteries`.

## Counting rule

1. Build the antisymmetric pairwise margin matrix M.
2. Enumerate intersections of active zero-probability and zero-expected-margin constraints; keep the first feasible probability vector.
3. Report p and sample one winner using the supplied seed.

**Variant used here:** Exact feasible-vertex search with rational arithmetic in Python and TypeScript. If several maximal lotteries exist, fixed constraint enumeration chooses one; this is not an earlier-candidate priority rule.

**Ties:** A fixed constraint enumeration chooses one feasible maximal lottery, including degenerate cases. The seed then samples a single winner; the full distribution is also returned. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "maximal-lotteries",
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

The sampled winner is **B** with seed 1. The distribution in the response describes the rule; the sampled name is one reproducible draw. The trace records intermediate totals, eliminations, comparisons, or the lottery used by this rule.

```json
{
  "method": "maximal-lotteries",
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
      "margins": [
        [
          0,
          -1,
          -1
        ],
        [
          1,
          0,
          5
        ],
        [
          1,
          -5,
          0
        ]
      ],
      "seed": 1
    }
  ],
  "lottery": [
    {
      "candidate": "A",
      "probability": 0.0
    },
    {
      "candidate": "B",
      "probability": 1.0
    },
    {
      "candidate": "C",
      "probability": 0.0
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="Maximal lotteries — complete algorithm">

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

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def solve_linear(matrix, rhs):
    n = len(rhs)
    augmented = [[Fraction(x) for x in row] + [Fraction(value)] for row, value in zip(matrix, rhs)]
    for column in range(n):
        pivot = next((row for row in range(column, n) if augmented[row][column]), None)
        if pivot is None:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value/divisor for value in augmented[column]]
        for row in range(n):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a-factor*b for a, b in zip(augmented[row], augmented[column])]
    return [row[-1] for row in augmented]

def count_maximal_lotteries(c, ballots, options):
    p = pairwise(c, ballots)
    n = len(c)
    margins = [[p[x][y]-p[y][x] for y in c] for x in c]
    # Vertices of {q>=0, sum(q)=1, q^T margins>=0}. A maximal lottery is
    # a minimax strategy of this skew-symmetric zero-sum game (value zero).
    constraints = [[int(i == j) for i in range(n)] for j in range(n)]
    constraints += [[margins[i][j] for i in range(n)] for j in range(n)]
    probabilities = None
    for active in itertools.combinations(range(2*n), n-1):
        solution = solve_linear([[1]*n] + [constraints[i] for i in active], [1]+[0]*(n-1))
        if solution is not None and all(x >= 0 for x in solution) and all(sum(solution[i]*margins[i][j] for i in range(n)) >= 0 for j in range(n)):
            probabilities = solution
            break
    if probabilities is None:
        raise RuntimeError("Maximal-lottery feasibility invariant failed")
    lottery = [{"candidate": x, "probability": float(probabilities[i])} for i, x in enumerate(c)]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"pairwise": p}, {"margins": margins, "seed": options["seed"]}], lottery=lottery)

election = {'method': 'maximal-lotteries', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_maximal_lotteries(election["candidates"], election["ballots"], election["options"])
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

function randomUnit(seed: number): number { return ((Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296; }

function sample(probabilities: number[], seed: number): number {
  const draw = randomUnit(seed);
  let cumulative = 0;
  for (let i = 0; i < probabilities.length; i++) { cumulative += probabilities[i]; if (draw < cumulative) return i; }
  return probabilities.length - 1;
}

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

function multiply(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[0], a[1] * b[1]); }

function negate(a: Fraction): Fraction { return [-a[0], a[1]]; }

function divide(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1], a[1] * b[0]); }

function gaussian(rows: number[][], rhs: number[]): Fraction[] | null {
  const n = rows.length;
  const a = rows.map((row, i) => [...row.map(v => fraction(BigInt(v))), fraction(BigInt(rhs[i]))]);
  for (let col = 0; col < n; col++) {
    const pivot = a.findIndex((row, i) => i >= col && row[col][0] !== 0n);
    if (pivot < 0) return null;
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const divisor = a[col][col];
    a[col] = a[col].map(v => divide(v, divisor));
    for (let i = 0; i < n; i++) if (i !== col) {
      const factor = a[i][col];
      a[i] = a[i].map((v, j) => add(v, negate(multiply(factor, a[col][j]))));
    }
  }
  return a.map(row => row[n]);
}

function* combinations(n: number, k: number, start = 0, prefix: number[] = []): Generator<number[]> {
  if (!k) { yield prefix; return; }
  for (let i = start; i <= n - k; i++) yield* combinations(n, k - 1, i + 1, [...prefix, i]);
}

export function countMaximalLotteries(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const n = ctx.candidates.length;
  const margins = ctx.candidates.map(c => ctx.candidates.map(d => matrix[c][d] - matrix[d][c]));
  const constraints = [
    ...ctx.candidates.map((_, i) => ctx.candidates.map((_, j) => i === j ? 1 : 0)),
    ...ctx.candidates.map((_, j) => ctx.candidates.map((_, i) => margins[i][j])),
  ];
  for (const active of combinations(2 * n, n - 1)) {
    const p = gaussian([Array(n).fill(1), ...active.map(i => constraints[i])], [1, ...active.map(() => 0)]);
    if (!p || p.some(v => v[0] < 0n)) continue;
    const feasible = constraints.slice(n).every(row => row.reduce((s, v, i) => add(s, multiply(fraction(BigInt(v)), p[i])), fraction(0n))[0] >= 0n);
    if (!feasible) continue;
    const probabilities = p.map(v => Number(v[0]) / Number(v[1]));
    const chosen = sample(probabilities, ctx.seed);
    return result(ctx, [ctx.candidates[chosen]], [{pairwise: matrix}, {margins, seed: ctx.seed}], probabilities);
  }
  throw new ElectionError('No maximal lottery found', 500);
}

const election: Context = {
  "method": "maximal-lotteries",
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
console.log(JSON.stringify(countMaximalLotteries(election), null, 2));
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/python/maximal-lotteries.py) or [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/examples/typescript/maximal-lotteries.ts) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. A first-place majority is protected by this rule. [Source](https://arxiv.org/abs/1503.00694). |
| [Rated majority](/criteria.md#majority-rated) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. A first-place majority is protected by this rule. [Source](https://arxiv.org/abs/1503.00694). |
| [Majority loser](/criteria.md#majority-loser) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. A strict last-place majority prevents election under the standard rule. [Source](https://arxiv.org/abs/1503.00694). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. A majority agreeing on a preferred group keeps the winner within that group. [Source](https://arxiv.org/abs/1503.00694). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. An existing strict head-to-head winner is selected. [Source](https://arxiv.org/abs/1503.00694). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. The standard rule excludes a candidate losing every pairwise comparison. [Source](https://arxiv.org/abs/1503.00694). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://arxiv.org/abs/1503.00694). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://arxiv.org/abs/1503.00694). |
| [Smith set](/criteria.md#smith) | pass | Here winning guarantees mean probability one and exclusions mean probability zero. The standard rule chooses only from the smallest strictly majority-dominant set. [Source](https://arxiv.org/abs/1503.00694). |
| [Smith independence](/criteria.md#smith-iia) | conditional | Assess the lottery distribution, not the winner sampled with a fixed seed. Requires an explicit ballot-domain, tie, or lottery interpretation; see the criterion guide. This is not an unconditional guarantee for the simulation. [Source](https://arxiv.org/abs/1503.00694). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | unverified | Assess the lottery distribution, not the winner sampled with a fixed seed. Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://arxiv.org/abs/1503.00694). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Assess the lottery distribution, not the winner sampled with a fixed seed. Removing a losing candidate can change which of the remaining candidates wins. [Source](https://arxiv.org/abs/1503.00694). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://arxiv.org/abs/1503.00694). |
| [Independence of clones](/criteria.md#clone-independence) | conditional | Composition consistency is proved for the maximal-lottery correspondence. It is not a blanket guarantee for a particular degenerate-lottery selector or a seeded winner. [Source](https://arxiv.org/abs/1503.00694). |
| [Monotonicity](/criteria.md#monotonicity) | unverified | No general mono-raise guarantee is asserted for the selected distribution. Comparison of a single seeded draw is not a monotonicity test. [Source](https://arxiv.org/abs/1503.00694). |
| [Consistency / reinforcement](/criteria.md#consistency) | conditional | The maximal-lottery correspondence satisfies population consistency. Selecting one feasible lottery arbitrarily in degenerate cases need not inherit every correspondence-level property. [Source](https://arxiv.org/abs/1503.00694). |
| [Participation](/criteria.md#participation) | fail | Assess the lottery distribution, not the winner sampled with a fixed seed. There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://arxiv.org/abs/1503.00694). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | Requires an explicit ballot-domain, tie, or lottery interpretation; see the criterion guide. This is not an unconditional guarantee for the simulation. [Source](https://arxiv.org/abs/1503.00694). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling all pairwise margins by the same positive factor preserves the entire feasible set of maximal lotteries. A consistent selector should choose the same distribution. [Source](https://arxiv.org/abs/1503.00694). |
| [Polynomial counting time](/criteria.md#polynomial-time) | conditional | Linear programming computes a maximal lottery in polynomial time. The self-contained demonstration instead enumerates supports and is exponential in candidates. [Source](https://arxiv.org/abs/1503.00694). |
| [Resolvability](/criteria.md#resolvability) | not-applicable | Randomness is part of the outcome rule, not merely a device for resolving exact counting ties. [Source](https://arxiv.org/abs/1503.00694). |
| [Summability](/criteria.md#summability) | pass | O(m²) pairwise totals are additive; Borda totals for Black and score totals for STAR add only O(m). Kemeny’s difficult optimization still occurs after aggregation. [Source](https://arxiv.org/abs/1503.00694). |
| [Later no harm](/criteria.md#later-no-harm) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://arxiv.org/abs/1503.00694). |
| [Later no help](/criteria.md#later-no-help) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://arxiv.org/abs/1503.00694). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://arxiv.org/abs/1503.00694). |

## Cost and limits

O(bm² + binomial(2m,m−1)m³) arithmetic operations for this vertex-enumeration demonstration; general linear-programming algorithms are polynomial.

At most 6 candidates; larger fields return HTTP 413. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Brandl, Brandt and Seedig: Consistent Probabilistic Social Choice](https://arxiv.org/abs/1503.00694)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
