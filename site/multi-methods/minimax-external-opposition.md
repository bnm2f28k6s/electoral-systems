# Minimax minimal size of external opposition

Score a whole committee by its weakest member-versus-outsider support. Choose the committee with the strongest weakest external contest.

**Ballot:** ranking. **API identifier:** `minimax-external-opposition` at `/multi/simulate`.

## Counting rule

1. Build pairwise support counts. Enumerate size-k committees W.
2. For each W, find the minimum p(a,b) across all a inside W and b outside W.
3. Maximize that committee minimum; select the first optimal committee under candidate priority.

**Implemented variant:** The Minimal Size of External Opposition rule M, also called SEO or committee Maximin. When every candidate is elected, there is no external opponent and the only committee is returned.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "minimax-external-opposition",
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

**The selected committee is A and B.** For committee A–B, every member has at least six supporters against every outsider. A–C and C–D have worst support four, and each other committee has worst support one. The best worst-case committee is A–B.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "minimax-external-opposition",
  "seats": 2,
  "winners": [
    "A",
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "pairwise": {
        "A": {
          "A": 0,
          "B": 9,
          "C": 6,
          "D": 6
        },
        "B": {
          "A": 1,
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
          "C": 1,
          "D": 0
        }
      }
    },
    {
      "committees": [
        {
          "committee": [
            "A",
            "B"
          ],
          "score": 6
        },
        {
          "committee": [
            "A",
            "C"
          ],
          "score": 4
        },
        {
          "committee": [
            "A",
            "D"
          ],
          "score": 1
        },
        {
          "committee": [
            "B",
            "C"
          ],
          "score": 1
        },
        {
          "committee": [
            "B",
            "D"
          ],
          "score": 1
        },
        {
          "committee": [
            "C",
            "D"
          ],
          "score": 4
        }
      ],
      "bestScore": 6,
      "tiedCommittees": [
        [
          "A",
          "B"
        ]
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go needs 1.23 or newer. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits. The server runs Python; the Go examples count locally without a server.

<CodeSelect title="Minimax minimal size of external opposition — complete algorithm">

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

def committee_optimum(c, committees, scores, minimize=False):
    optimum = (min if minimize else max)(scores)
    tied = [list(committee) for committee, score in zip(committees, scores) if score == optimum]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [{"committee": list(committee), "score": float(score) if isinstance(score, Fraction) else score} for committee, score in zip(committees, scores)], "bestScore": float(optimum) if isinstance(optimum, Fraction) else optimum, "tiedCommittees": tied}]}

def count_minimax_external_opposition(c, ballots, seats, options):
    matrix = pairwise(c, ballots)
    total = sum(b["count"] for b in ballots)
    committees = list(itertools.combinations(c, seats))
    scores = [min([matrix[x][y] for x in committee for y in c if y not in committee] or [total]) for committee in committees]
    counted = committee_optimum(c, committees, scores)
    counted["trace"].insert(0, {"pairwise": matrix})
    return counted

election = {'method': 'minimax-external-opposition', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_minimax_external_opposition(election["candidates"], election["ballots"], election["seats"], election["options"])
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

export function countMinimaxExternalOpposition(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  return optimize(ctx, committee => {
    const outside = ctx.candidates.filter(c => !committee.includes(c));
    const minimum = outside.length ? Math.min(...committee.flatMap(a => outside.map(b => matrix[a][b]))) : ctx.total;
    return fraction(minimum);
  }, [{pairwise: matrix}]);
}

const election: Context = {
  "method": "minimax-external-opposition",
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
console.log(JSON.stringify(countMinimaxExternalOpposition(election), null, 2));
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

func CountMinimaxExternalOpposition(request any) (map[string]any, error) {
	return run(request, "minimax-external-opposition", countMinimaxExternalOpposition)
}

func countMinimaxExternalOpposition(x context) map[string]any {
	m := pairwise(x)
	cs := combinations(x.c, x.seats)
	scores := []*big.Rat{}
	for _, c := range cs {
		v := x.total
		for _, a := range c {
			for _, b := range difference(x.c, c) {
				if m[a][b] < v {
					v = m[a][b]
				}
			}
		}
		scores = append(scores, rat(v))
	}
	return optimize(x, cs, scores, false, trace{{"pairwise": m}})
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

func difference(a, b []string) []string {
	r := []string{}
	for _, x := range a {
		if !contains(b, x) {
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

func number(r *big.Rat) float64 { v, _ := r.Float64(); return v }

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

func pairwise(x context) map[string]map[string]int64 {
	m := map[string]map[string]int64{}
	for _, c := range x.c {
		m[c] = map[string]int64{}
		for _, d := range x.c {
			m[c][d] = 0
		}
	}
	for _, b := range x.ballots {
		for i, c := range b.ranking {
			for _, d := range b.ranking[i+1:] {
				m[c][d] += b.count
			}
		}
	}
	return m
}

func main() {
	var request any
	if err := json.Unmarshal([]byte("{\"method\": \"minimax-external-opposition\", \"seats\": 2, \"candidates\": [\"A\", \"B\", \"C\", \"D\"], \"ballots\": [{\"ranking\": [\"A\", \"B\", \"C\", \"D\"], \"count\": 6}, {\"ranking\": [\"C\", \"D\", \"A\", \"B\"], \"count\": 3}, {\"ranking\": [\"D\", \"C\", \"B\", \"A\"], \"count\": 1}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"limit\": 1, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountMinimaxExternalOpposition(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/python/minimax-external-opposition.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/typescript/minimax-external-opposition.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/go/minimax-external-opposition.go) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | fail | The committee Maximin correspondence fails non-crossing/candidate monotonicity in the primary analysis: a support improvement can alter the optimal committee boundary. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | pass | Under the ordinal replacement test, unanimous A above B ensures that a winning outcome including B does not exclude A from every possible winning committee. Fixed priority may select just one member of that correspondence. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | pass | Under the ordinal replacement test, if everyone ranks A above B, an elected B cannot be retained while A is absent in the standard rule. This is candidate dominance, not an unstated utility comparison between whole committees. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | fail | Balanced first-choice support need not determine positional totals or weakest pairwise contests. The cited ordinal analyses provide consensus-committee failures. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | pass | A strict Gehrlein committee has every external support above N/2. Any different committee includes an outsider and excludes an insider, so its external minimum is below N/2; it cannot tie or beat that committee. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | fail | Changing k changes which contests are internal and which determine the minimum external support. The primary paper gives failures of committee monotonicity. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | fail | Taking a minimum is not an additive committee objective. The primary comparison proves failure for both the Simpson and committee Maximin correspondences. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | A unanimously top-ranked k-set is among the optimizing committees. Rules using only first-place or worst-pairwise totals can still leave other co-winning committees. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | pass | When all voters put the same k-set above every outsider, Borda/Bloc totals or every external pairwise support strictly favor that set over any committee containing an outsider. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | pass | A strict majority putting the same size-k set first gives its members a strict Bloc-score advantage over outsiders, or gives that committee an external pairwise minimum above N/2 while each alternative crosses a losing boundary. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | fail | The self-contained exact implementation enumerates candidate subsets, committees or committee pairs. Its documented small input cap controls runtime but is not a polynomial-time algorithm for unbounded candidate counts. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | The O(m²) pairwise-support matrix adds across precincts and determines all candidate or committee minima. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

O(bm² + binomial(m,k)k(m−k)).

Exact committee enumeration is limited to 8 candidates, in addition to the shared API limits. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Bubboloni, Diss and Gori: the committee Maximin rule](https://flore.unifi.it/handle/2158/1175914)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
