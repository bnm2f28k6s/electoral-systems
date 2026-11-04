# CPO-STV

Compare possible committees after transferring surplus votes of candidates common to both. Use those committee contests to resolve the election.

**Ballot:** ranking. **API identifier:** `cpo-stv` at `/multi/simulate`.

## Counting rule

1. Enumerate all size-k committees. For each pair, exclude candidates outside their union.
2. Allocate ballots by highest continuing preference; transfer surpluses only from quota-reaching candidates common to both committees.
3. Compare the resulting support of the two committees; elect the committee whose worst pairwise defeat margin is smallest.

**Implemented variant:** Comparison of Pairs of Outcomes using integer Droop quota and fractional inclusive Gregory transfers; cycles use an explicitly chosen minimax-margin completion. CPO-STV is a family unless its completion and transfer rules are specified.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "cpo-stv",
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

**The selected committee is A and C.** For the comparison of A–C against A–B, D is excluded and its ballot goes to C. Common member A keeps its quota of four and transfers two votes to B. The totals for the two committees are eight for A–C and six for A–B. Comparing all committees selects A–C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "cpo-stv",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "quota": 4,
      "support": [
        [
          0.0,
          6.0,
          6.0,
          6.0,
          6.0,
          6.0
        ],
        [
          8.0,
          0.0,
          9.0,
          10.0,
          9.0,
          9.0
        ],
        [
          8.0,
          5.0,
          0.0,
          7.0,
          10.0,
          7.0
        ],
        [
          4.0,
          4.0,
          3.0,
          0.0,
          9.0,
          9.0
        ],
        [
          4.0,
          1.0,
          4.0,
          5.0,
          0.0,
          7.0
        ],
        [
          4.0,
          4.0,
          4.0,
          4.0,
          4.0,
          0.0
        ]
      ],
      "comparisonTies": []
    },
    {
      "committees": [
        {
          "committee": [
            "A",
            "B"
          ],
          "score": 2.0
        },
        {
          "committee": [
            "A",
            "C"
          ],
          "score": 0.0
        },
        {
          "committee": [
            "A",
            "D"
          ],
          "score": 4.0
        },
        {
          "committee": [
            "B",
            "C"
          ],
          "score": 6.0
        },
        {
          "committee": [
            "B",
            "D"
          ],
          "score": 8.0
        },
        {
          "committee": [
            "C",
            "D"
          ],
          "score": 5.0
        }
      ],
      "bestScore": 0.0,
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

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go needs 1.23 or newer. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits. The server runs Python; the Go examples count locally without a server.

<CodeSelect title="CPO-STV — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def committee_optimum(c, committees, scores, minimize=False):
    optimum = (min if minimize else max)(scores)
    tied = [list(committee) for committee, score in zip(committees, scores) if score == optimum]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [{"committee": list(committee), "score": float(score) if isinstance(score, Fraction) else score} for committee, score in zip(committees, scores)], "bestScore": float(optimum) if isinstance(optimum, Fraction) else optimum, "tiedCommittees": tied}]}

def cpo_support(c, ballots, first, second, quota, decisions=None):
    active = [x for x in c if x in first or x in second]
    common = [x for x in c if x in first and x in second]
    weights = [Fraction(b["count"]) for b in ballots]
    retained = Fraction(0)
    while True:
        choices = [next(x for x in b["ranking"] if x in active) for b in ballots]
        tally = {x: sum((w for choice, w in zip(choices, weights) if choice == x), Fraction(0)) for x in active}
        eligible = [x for x in common if x in active and tally[x] > quota]
        if not eligible:
            break
        high = max(tally[x] for x in eligible)
        tied = [x for x in eligible if tally[x] == high]
        winner = tied[0]
        if decisions is not None and len(tied) > 1:
            decisions.append({"candidates": tied, "selected": winner})
        factor = (tally[winner]-quota)/tally[winner]
        weights = [w*factor if choice == winner else w for choice, w in zip(choices, weights)]
        retained += quota
        active.remove(winner)
    return retained+sum(tally[x] for x in active if x in first), retained+sum(tally[x] for x in active if x in second)

def count_cpo_stv(c, ballots, seats, options):
    committees = list(itertools.combinations(c, seats))
    quota = sum(b["count"] for b in ballots)//(seats+1)+1
    support = [[Fraction(0) for second in committees] for first in committees]
    comparison_ties = []
    for i, first in enumerate(committees):
        for j in range(i+1, len(committees)):
            decisions = []
            support[i][j], support[j][i] = cpo_support(c, ballots, first, committees[j], quota, decisions)
            if decisions:
                comparison_ties.append({"first": list(first), "second": list(committees[j]), "decisions": decisions})
    worst = [max([Fraction(0)]+[support[j][i]-support[i][j] for j in range(len(committees)) if i != j]) for i in range(len(committees))]
    counted = committee_optimum(c, committees, worst, True)
    counted["tie"] |= bool(comparison_ties)
    counted["trace"].insert(0, {"quota": quota, "support": [[float(value) for value in row] for row in support], "comparisonTies": comparison_ties})
    return counted

election = {'method': 'cpo-stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_cpo_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
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

function add(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);}

function negate(a: Fraction): Fraction {return [-a[0], a[1]];}

function subtract(a: Fraction, b: Fraction): Fraction {return add(a, negate(b));}

function multiply(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[0], a[1] * b[1]);}

function divide(a: Fraction, b: Fraction): Fraction {return fraction(a[0] * b[1], a[1] * b[0]);}

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

function result(ctx: Context, winners: string[], tie: boolean, trace: Trace): SimulationResult {
  return {method: ctx.method, seats: ctx.seats, winners: ctx.candidates.filter(c => winners.includes(c)), tie, trace};
}

function* combinations<T>(items: T[], k: number, start = 0, prefix: T[] = []): Generator<T[]> {
  if (!k) {yield prefix; return;}
  for (let i = start; i <= items.length - k; i++) yield* combinations(items, k - 1, i + 1, [...prefix, items[i]]);
}

function optimize(ctx: Context, scorer: (committee: string[]) => Fraction, prefix: Trace = [], minimize = false): SimulationResult {
  let optimum: Fraction | null = null;
  const tied: string[][] = [];
  const scores: {committee: string[]; score: number}[] = [];
  for (const committee of combinations(ctx.candidates, ctx.seats)) {
    const score = scorer(committee);
    scores.push({committee, score: asNumber(score)});
    const comparison = optimum === null ? (minimize ? -1 : 1) : compare(score, optimum);
    if ((minimize ? -comparison : comparison) > 0) {optimum = score; tied.length = 0; tied.push(committee);}
    else if (comparison === 0) tied.push(committee);
  }
  return result(ctx, tied[0], tied.length > 1,
    [...prefix, {committees: scores, bestScore: asNumber(optimum!), tiedCommittees: tied}]);
}

function cpoSupport(ctx: Context, first: string[], second: string[], quota: number, decisions: Trace = []): [Fraction, Fraction] {
  const active = ctx.candidates.filter(c => first.includes(c) || second.includes(c));
  const common = ctx.candidates.filter(c => first.includes(c) && second.includes(c));
  let weights = ctx.ballots.map(b => fraction(b.count)), retained = fraction(0);
  let tally: Record<string, Fraction> = {};
  while (true) {
    const choices = ctx.ballots.map(b => b.ranking!.find(c => active.includes(c))!);
    tally = Object.fromEntries(active.map(c => {
      let score = fraction(0); choices.forEach((choice, i) => {if (choice === c) score = add(score, weights[i]);}); return [c, score];
    }));
    const eligible = common.filter(c => active.includes(c) && compare(tally[c], fraction(quota)) > 0);
    if (!eligible.length) break;
    let winner = eligible[0];
    for (const c of eligible) if (compare(tally[c], tally[winner]) > 0) winner = c;
    const tied = eligible.filter(c => compare(tally[c], tally[winner]) === 0);
    if (tied.length > 1) decisions.push({candidates: tied, selected: winner});
    const factor = divide(subtract(tally[winner], fraction(quota)), tally[winner]);
    weights = weights.map((w, i) => choices[i] === winner ? multiply(w, factor) : w);
    retained = add(retained, fraction(quota)); active.splice(active.indexOf(winner), 1);
  }
  let left = retained, right = retained;
  for (const c of active) {if (first.includes(c)) left = add(left, tally[c]); if (second.includes(c)) right = add(right, tally[c]);}
  return [left, right];
}

export function countCpoStv(ctx: Context): SimulationResult {
  const committees = [...combinations(ctx.candidates, ctx.seats)];
  const quota = Math.floor(ctx.total / (ctx.seats + 1)) + 1;
  const support = committees.map(() => committees.map(() => fraction(0)));
  const comparisonTies: Trace = [];
  for (let i = 0; i < committees.length; i++) for (let j = i + 1; j < committees.length; j++) {
    const decisions: Trace = [];
    [support[i][j], support[j][i]] = cpoSupport(ctx, committees[i], committees[j], quota, decisions);
    if (decisions.length) comparisonTies.push({first: committees[i], second: committees[j], decisions});
  }
  const worst = committees.map((_, i) => {
    let value = fraction(0);
    for (let j = 0; j < committees.length; j++) if (i !== j) {const loss = subtract(support[j][i], support[i][j]); if (compare(loss, value) > 0) value = loss;}
    return value;
  });
  const answer = optimize(ctx, committee => worst[committees.findIndex(other => other.every((c, i) => c === committee[i]))],
    [{quota, support: support.map(row => row.map(asNumber)), comparisonTies}], true);
  answer.tie ||= comparisonTies.length > 0;
  return answer;
}

const election: Context = {
  "method": "cpo-stv",
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
console.log(JSON.stringify(countCpoStv(election), null, 2));
```

```go
// Go 1.23+. Save as example.go and run: go run example.go
// Self-contained count, extracted from the validated Go engine.
package main

import (
	json "encoding/json"
	math "math"
	big "math/big"
	os "os"
	strings "strings"
	unicode "unicode"
	utf8 "unicode/utf8"
)

func CountCpoStv(request any) (map[string]any, error) { return run(request, "cpo-stv", countCpoStv) }

func cpoSupport(x context, first, second []string, q *big.Rat) (*big.Rat, *big.Rat, trace) {
	active := []string{}
	common := []string{}
	for _, c := range x.c {
		if contains(first, c) || contains(second, c) {
			active = append(active, c)
		}
		if contains(first, c) && contains(second, c) {
			common = append(common, c)
		}
	}
	w := weights(x)
	retained := rat(0)
	decisions := trace{}
	var t map[string]*big.Rat
	for {
		var choices []string
		choices, t = choicesTally(x, active, w)
		eligible := []string{}
		for _, c := range common {
			if contains(active, c) && t[c].Cmp(q) > 0 {
				eligible = append(eligible, c)
			}
		}
		if len(eligible) == 0 {
			break
		}
		tied := best(eligible, t, false)
		winner := tied[0]
		if len(tied) > 1 {
			decisions = append(decisions, map[string]any{"candidates": tied, "selected": winner})
		}
		f := div(sub(t[winner], q), t[winner])
		transfer(w, choices, winner, f)
		retained = add(retained, q)
		active = without(active, winner)
	}
	left, right := retained, retained
	for _, c := range active {
		if contains(first, c) {
			left = add(left, t[c])
		}
		if contains(second, c) {
			right = add(right, t[c])
		}
	}
	return left, right, decisions
}

func ratMatrix(n int) [][]*big.Rat {
	r := make([][]*big.Rat, n)
	for i := range r {
		r[i] = make([]*big.Rat, n)
		for j := range r[i] {
			r[i][j] = rat(0)
		}
	}
	return r
}

func matrixNumbers(m [][]*big.Rat) [][]float64 {
	r := make([][]float64, len(m))
	for i := range m {
		r[i] = numbers(m[i])
	}
	return r
}

func countCpoStv(x context) map[string]any {
	cs := combinations(x.c, x.seats)
	q := rat(x.total/int64(x.seats+1) + 1)
	support := ratMatrix(len(cs))
	comparisonTies := trace{}
	for i, first := range cs {
		for j := i + 1; j < len(cs); j++ {
			a, b, decisions := cpoSupport(x, first, cs[j], q)
			support[i][j] = a
			support[j][i] = b
			if len(decisions) > 0 {
				comparisonTies = append(comparisonTies, map[string]any{"first": first, "second": cs[j], "decisions": decisions})
			}
		}
	}
	worst := []*big.Rat{}
	for i := range cs {
		v := rat(0)
		for j := range cs {
			loss := sub(support[j][i], support[i][j])
			if loss.Cmp(v) > 0 {
				v = loss
			}
		}
		worst = append(worst, v)
	}
	r := optimize(x, cs, worst, true, trace{{"quota": number(q), "support": matrixNumbers(support), "comparisonTies": comparisonTies}})
	r["tie"] = r["tie"].(bool) || len(comparisonTies) > 0
	return r
}

type ElectionError struct {
	Status  int
	Message string
}

func (e *ElectionError) Error() string { return e.Message }

type ballot struct {
	ranking, approvals []string
	choice             string
	values             map[string]int64
	count              int64
}

type context struct {
	method                               string
	c                                    []string
	seats                                int
	ballots                              []ballot
	maxScore, budget, limit, seed, total int64
}

type trace = []map[string]any

func invalid(message string, status ...int) error {
	s := 400
	if len(status) > 0 {
		s = status[0]
	}
	return &ElectionError{s, message}
}

func knownMethod(s string) bool {
	switch s {
	case "approval", "proportional-approval", "sequential-proportional-approval", "reweighted-range", "stv", "cpo-stv", "schulze-stv", "phragmen", "k-borda", "bloc", "quota-borda", "expanding-approvals", "minimax", "minimax-external-opposition", "single-non-transferable", "limited-vote", "cumulative", "sortition", "multiple-random-ballots":
		return true
	}
	return false
}

func keys(m map[string]any, allowed string) bool {
	names := strings.Split(allowed, "|")
	for k := range m {
		if !contains(names, k) {
			return false
		}
	}
	return true
}

func integer(v any, low, high int64) (int64, bool) {
	var f float64
	switch x := v.(type) {
	case float64:
		f = x
	case int:
		f = float64(x)
	case int64:
		f = float64(x)
	case json.Number:
		var e error
		f, e = x.Float64()
		if e != nil {
			return 0, false
		}
	default:
		return 0, false
	}
	if math.IsNaN(f) || math.IsInf(f, 0) || math.Trunc(f) != f || math.Abs(f) > 9007199254740991 || f < float64(low) || f > float64(high) {
		return 0, false
	}
	return int64(f), true
}

func array(v any) ([]any, bool) {
	switch a := v.(type) {
	case []any:
		return a, true
	case []string:
		r := make([]any, len(a))
		for i, s := range a {
			r[i] = s
		}
		return r, true
	}
	return nil, false
}

func contains(a []string, s string) bool {
	for _, x := range a {
		if x == s {
			return true
		}
	}
	return false
}

func without(a []string, s string) []string {
	r := []string{}
	for _, x := range a {
		if x != s {
			r = append(r, x)
		}
	}
	return r
}

func validate(request any) (context, error) {
	x := context{}
	r, ok := request.(map[string]any)
	if !ok {
		return x, invalid("Request must be an object")
	}
	if !keys(r, "method|candidates|seats|ballots|options") {
		return x, invalid("Unknown request field")
	}
	x.method, ok = r["method"].(string)
	if !ok || !knownMethod(x.method) {
		return x, invalid("Unknown multi-winner method")
	}
	cs, ok := array(r["candidates"])
	if !ok || len(cs) == 0 {
		return x, invalid("Supply at least one candidate")
	}
	if len(cs) > 32 {
		return x, invalid("At most 32 candidates", 413)
	}
	for _, v := range cs {
		s, ok := v.(string)
		if !ok || utf8.RuneCountInString(s) > 100 || strings.TrimFunc(s, func(r rune) bool { return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f) }) == "" || contains(x.c, s) {
			return x, invalid("Candidate IDs must be unique nonempty strings of at most 100 characters")
		}
		x.c = append(x.c, s)
	}
	n, ok := integer(r["seats"], 1, int64(len(x.c)))
	if !ok {
		return x, invalid("seats must be an integer from 1 to candidate count")
	}
	x.seats = int(n)
	opts := map[string]any{}
	if v, exists := r["options"]; exists {
		opts, ok = v.(map[string]any)
		if !ok {
			return x, invalid("options must be an object")
		}
	}
	if !keys(opts, "maxScore|budget|limit|seed") {
		return x, invalid("Unknown option")
	}
	lim := int64(x.seats - 1)
	if lim < 1 {
		lim = 1
	}
	for _, o := range []struct {
		k              string
		def, low, high int64
		out            *int64
	}{{"maxScore", 5, 1, 100, &x.maxScore}, {"budget", 100, 1, 1000000, &x.budget}, {"limit", lim, 1, 32, &x.limit}, {"seed", 1, 0, 4294967295, &x.seed}} {
		v, exists := opts[o.k]
		if !exists {
			v = o.def
		}
		z, valid := integer(v, o.low, o.high)
		if !valid {
			return x, invalid(o.k + " is outside its integer bounds")
		}
		*o.out = z
	}
	if x.method == "limited-vote" && x.limit > lim {
		return x, invalid("Limited vote limit must be below seats")
	}
	bs, ok := array(r["ballots"])
	if !ok {
		return x, invalid("ballots must be an array")
	}
	if len(bs) > 10000 {
		return x, invalid("At most 10000 ballot groups", 413)
	}
	if (x.method == "sortition") != (len(bs) == 0) {
		return x, invalid("Only sortition accepts an empty ballot array, and sortition requires it")
	}
	expected := "ranking"
	switch x.method {
	case "approval", "proportional-approval", "sequential-proportional-approval", "phragmen", "limited-vote":
		expected = "approvals"
	case "reweighted-range":
		expected = "scores"
	case "cumulative":
		expected = "votes"
	}
	for _, v := range bs {
		b, ok := v.(map[string]any)
		if !ok {
			return x, invalid("Each ballot must be an object")
		}
		if !keys(b, "ranking|approvals|choice|scores|votes|count") {
			return x, invalid("Unknown ballot field")
		}
		field := ""
		for _, f := range []string{"ranking", "approvals", "choice", "scores", "votes"} {
			if _, has := b[f]; has {
				if field != "" {
					return x, invalid("Each ballot needs exactly one format")
				}
				field = f
			}
		}
		if field == "" {
			return x, invalid("Each ballot needs exactly one format")
		}
		if field != expected && !(x.method == "single-non-transferable" && field == "choice") {
			return x, invalid("Wrong ballot format for " + x.method)
		}
		count := int64(1)
		if v, has := b["count"]; has {
			count, ok = integer(v, 1, 1000000)
			if !ok {
				return x, invalid("count must be a positive integer at most 1000000")
			}
		}
		x.total += count
		if x.total > 1000000 {
			return x, invalid("At most 1000000 represented voters", 413)
		}
		nb := ballot{count: count}
		switch field {
		case "ranking", "approvals":
			a, ok := array(b[field])
			if !ok {
				return x, invalid(field + " must be an array")
			}
			ss := []string{}
			for _, v := range a {
				s, ok := v.(string)
				if !ok || !contains(x.c, s) || contains(ss, s) {
					return x, invalid(field + " contains an invalid or duplicate candidate")
				}
				ss = append(ss, s)
			}
			if field == "ranking" {
				if len(ss) != len(x.c) {
					return x, invalid("ranking must list every candidate exactly once")
				}
				nb.ranking = ss
			} else {
				if x.method == "limited-vote" && int64(len(ss)) > x.limit {
					return x, invalid("Too many approvals for limited vote")
				}
				nb.approvals = ss
			}
		case "choice":
			s, ok := b[field].(string)
			if !ok || !contains(x.c, s) {
				return x, invalid("choice must name a candidate")
			}
			nb.choice = s
		default:
			vs, ok := b[field].(map[string]any)
			if !ok || len(vs) != len(x.c) {
				return x, invalid(field + " must contain every candidate")
			}
			nb.values = map[string]int64{}
			var sum int64
			for _, c := range x.c {
				n, ok := integer(vs[c], 0, 9007199254740991)
				if !ok {
					return x, invalid(field + " must contain nonnegative integer values")
				}
				if field == "scores" && n > x.maxScore {
					return x, invalid("Scores exceeded")
				}
				if field == "votes" && n > x.budget {
					return x, invalid("Cumulative vote budget exceeded")
				}
				sum += n
				nb.values[c] = n
			}
			if field == "votes" && sum > x.budget {
				return x, invalid("Cumulative vote budget exceeded")
			}
		}
		x.ballots = append(x.ballots, nb)
	}
	if (x.method == "proportional-approval" || x.method == "minimax-external-opposition") && len(x.c) > 8 {
		return x, invalid("Exact committee enumeration supports at most 8 candidates", 413)
	}
	if (x.method == "cpo-stv" || x.method == "schulze-stv") && (len(x.c) > 6 || len(bs) > 100) {
		return x, invalid("Exact STV comparisons support at most 6 candidates and 100 ballot groups", 413)
	}
	return x, nil
}

func run(request any, method string, count func(context) map[string]any) (map[string]any, error) {
	x, e := validate(request)
	if e != nil {
		return nil, e
	}
	if x.method != method {
		return nil, invalid("Expected method " + method)
	}
	return count(x), nil
}

func result(x context, elected []string, tie bool, t trace) map[string]any {
	w := []string{}
	for _, c := range x.c {
		if contains(elected, c) {
			w = append(w, c)
		}
	}
	return map[string]any{"method": x.method, "seats": x.seats, "winners": w, "tie": tie, "trace": t}
}

func rat(n int64) *big.Rat { return new(big.Rat).SetInt64(n) }

func add(a, b *big.Rat) *big.Rat { return new(big.Rat).Add(a, b) }

func sub(a, b *big.Rat) *big.Rat { return new(big.Rat).Sub(a, b) }

func mul(a, b *big.Rat) *big.Rat { return new(big.Rat).Mul(a, b) }

func div(a, b *big.Rat) *big.Rat { return new(big.Rat).Quo(a, b) }

func number(r *big.Rat) float64 { v, _ := r.Float64(); return v }

func numbers(a []*big.Rat) []float64 {
	r := make([]float64, len(a))
	for i, v := range a {
		r[i] = number(v)
	}
	return r
}

func zeros(c []string) map[string]*big.Rat {
	r := map[string]*big.Rat{}
	for _, s := range c {
		r[s] = rat(0)
	}
	return r
}

func best(c []string, t map[string]*big.Rat, min bool) []string {
	r := []string{}
	var value *big.Rat
	for _, s := range c {
		v := t[s]
		if v == nil {
			continue
		}
		cmp := 1
		if value != nil {
			cmp = v.Cmp(value)
			if min {
				cmp = -cmp
			}
		}
		if cmp > 0 {
			r = []string{s}
			value = v
		} else if cmp == 0 {
			r = append(r, s)
		}
	}
	return r
}

func combinations(c []string, k int) [][]string {
	r := [][]string{}
	var visit func(int, []string)
	visit = func(start int, p []string) {
		if len(p) == k {
			r = append(r, append([]string{}, p...))
			return
		}
		for i := start; i <= len(c)-(k-len(p)); i++ {
			visit(i+1, append(p, c[i]))
		}
	}
	visit(0, nil)
	return r
}

func optimize(x context, cs [][]string, scores []*big.Rat, min bool, prefix trace) map[string]any {
	var opt *big.Rat
	tied := [][]string{}
	rows := []map[string]any{}
	for i, c := range cs {
		s := scores[i]
		rows = append(rows, map[string]any{"committee": c, "score": number(s)})
		cmp := 1
		if opt != nil {
			cmp = s.Cmp(opt)
			if min {
				cmp = -cmp
			}
		}
		if cmp > 0 {
			opt = s
			tied = [][]string{c}
		} else if cmp == 0 {
			tied = append(tied, c)
		}
	}
	return result(x, tied[0], len(tied) > 1, append(prefix, map[string]any{"committees": rows, "bestScore": number(opt), "tiedCommittees": tied}))
}

func weights(x context) []*big.Rat {
	w := make([]*big.Rat, len(x.ballots))
	for i, b := range x.ballots {
		w[i] = rat(b.count)
	}
	return w
}

func choicesTally(x context, active []string, w []*big.Rat) ([]string, map[string]*big.Rat) {
	choices := make([]string, len(x.ballots))
	t := zeros(active)
	for i, b := range x.ballots {
		for _, c := range b.ranking {
			if contains(active, c) {
				choices[i] = c
				t[c] = add(t[c], w[i])
				break
			}
		}
	}
	return choices, t
}

func transfer(w []*big.Rat, choices []string, winner string, factor *big.Rat) {
	for i, c := range choices {
		if c == winner {
			w[i] = mul(w[i], factor)
		}
	}
}

func main() {
	var request any
	if err := json.Unmarshal([]byte("{\"method\": \"cpo-stv\", \"seats\": 2, \"candidates\": [\"A\", \"B\", \"C\", \"D\"], \"ballots\": [{\"ranking\": [\"A\", \"B\", \"C\", \"D\"], \"count\": 6}, {\"ranking\": [\"C\", \"D\", \"A\", \"B\"], \"count\": 3}, {\"ranking\": [\"D\", \"C\", \"B\", \"A\"], \"count\": 1}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"limit\": 1, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountCpoStv(request)
	if err != nil {
		panic(err)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(answer); err != nil {
		panic(err)
	}
}
```

</CodeSelect>

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/python/cpo-stv.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/typescript/cpo-stv.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/go/cpo-stv.go) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | unverified | Tideman’s proposal and the EAR review distinguish the intended proportional behavior from a full PSC proof. The quota and chosen minimax completion must be part of any exact claim; no theorem is inferred from the label CPO-STV. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | Committee comparisons or strongest paths are not additive final objectives. No exact-variant proof or direct counterexample is supplied here; Condorcet completion alone is not a consistency proof. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | conditional | Exact fractional transfers do not remove the effect of integer Droop rounding. Replicating ballots need not scale floor(N/(k+1))+1 proportionally; no unconditional homogeneity claim is made for this variant. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | fail | With priority order D,C,B,A, three seats and one A&gt;B&gt;C&gt;D ballot, integer Droop is 1 and the implementation selects &#123;A,C,D&#125;, not the unanimous top set &#123;A,B,C&#125;. Zero-weight or equal-comparison ties after retaining A’s quota expose the small-electorate failure. Unrounded-quota theorems do not prove this accepted-input variant strongly unanimous. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | fail | The self-contained exact implementation enumerates candidate subsets, committees or committee pairs. Its documented small input cap controls runtime but is not a polynomial-time algorithm for unbounded candidate counts. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

Exhaustive committee pairs: O(C²bm²) arithmetic operations for C=binomial(m,k), before minor scoring work.

Exact committee comparisons are limited to 6 candidates and 100 ballot groups, in addition to the shared API limits. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Tideman: The Single Transferable Vote (1995)](https://rangevoting.org/TidemanSTVJEconPersp195.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
