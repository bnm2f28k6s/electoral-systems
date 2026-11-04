# Phragmén’s sequential rule

Each elected candidate carries one unit of representation load. Share that load among approving voters while keeping the maximum voter load as small as possible at each step.

**Ballot:** approvals. **API identifier:** `phragmen` at `/multi/simulate`.

## Counting rule

1. Start with zero load for each voter.
2. For each unelected candidate, find the smallest level L such that raising approving voters with lower loads up to L can absorb one unit of load.
3. Elect the candidate with the smallest such L, update those approving voters’ loads, and repeat.

**Implemented variant:** Sequential Phragmén on approval ballots (seq-Phragmén), not the global leximax optimization or Phragmén’s distinct ranked methods. Unsupported seats are filled by published priority when no supported candidate remains.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "phragmen",
  "seats": 2,
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "ballots": [
    {
      "approvals": [
        "A",
        "B"
      ],
      "count": 6
    },
    {
      "approvals": [
        "C",
        "D"
      ],
      "count": 3
    },
    {
      "approvals": [
        "D"
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

**The selected committee is A and D.** A and B each have six supporters, so either can spread one seat's load over six voters. Priority selects A. A second seat for B would bring those same voters to load 1/3 each, while D can spread it over four previously uncharged voters at load 1/4. D takes the second seat.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "phragmen",
  "seats": 2,
  "winners": [
    "A",
    "D"
  ],
  "tie": true,
  "trace": [
    {
      "round": 1,
      "loadLevels": {
        "A": 0.16666666666666666,
        "B": 0.16666666666666666,
        "C": 0.3333333333333333,
        "D": 0.25
      },
      "selected": "A",
      "tied": [
        "A",
        "B"
      ],
      "loads": [
        0.16666666666666666,
        0.0,
        0.0
      ]
    },
    {
      "round": 2,
      "loadLevels": {
        "B": 0.3333333333333333,
        "C": 0.3333333333333333,
        "D": 0.25
      },
      "selected": "D",
      "tied": [
        "D"
      ],
      "loads": [
        0.16666666666666666,
        0.25,
        0.25
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go needs 1.23 or newer. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits. The server runs Python; the Go examples count locally without a server.

<CodeSelect title="Phragmén’s sequential rule — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def count_phragmen(c, ballots, seats, options):
    loads = [Fraction(0) for b in ballots]
    elected, trace, tie = [], [], False
    for step in range(seats):
        levels = {}
        for x in c:
            if x in elected:
                continue
            support = sum(b["count"] for b in ballots if x in b["approvals"])
            levels[x] = (1+sum((load*b["count"] for b, load in zip(ballots, loads) if x in b["approvals"]), Fraction(0)))/support if support else None
        finite = [v for v in levels.values() if v is not None]
        low = min(finite) if finite else None
        tied = [x for x in c if x in levels and levels[x] == low]
        winner = tied[0]
        elected.append(winner)
        tie |= len(tied) > 1
        if low is not None:
            loads = [low if winner in b["approvals"] else load for b, load in zip(ballots, loads)]
        trace.append({"round": step+1, "loadLevels": {x: float(v) if v is not None else None for x, v in levels.items()}, "selected": winner, "tied": tied, "loads": [float(v) for v in loads]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'phragmen', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'approvals': ['A', 'B'], 'count': 6}, {'approvals': ['C', 'D'], 'count': 3}, {'approvals': ['D'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_phragmen(election["candidates"], election["ballots"], election["seats"], election["options"])
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

export function countPhragmen(ctx: Context): SimulationResult {
  let loads = ctx.ballots.map(() => fraction(0));
  const elected: string[] = [], trace: Trace = [];
  let tie = false;
  for (let step = 0; step < ctx.seats; step++) {
    const candidates = ctx.candidates.filter(c => !elected.includes(c));
    const levels: Record<string, Fraction | null> = Object.fromEntries(candidates.map(c => {
      const support = ctx.ballots.reduce((sum, b) => sum + (b.approvals!.includes(c) ? b.count : 0), 0);
      let load = fraction(1);
      ctx.ballots.forEach((b, i) => {if (b.approvals!.includes(c)) load = add(load, multiply(loads[i], fraction(b.count)));});
      return [c, support ? divide(load, fraction(support)) : null];
    }));
    let low: Fraction | null = null;
    for (const c of candidates) if (levels[c] !== null && (low === null || compare(levels[c]!, low) < 0)) low = levels[c];
    const tied = candidates.filter(c => low === null ? levels[c] === null : levels[c] !== null && compare(levels[c]!, low!) === 0);
    const selected = tied[0]; elected.push(selected); tie ||= tied.length > 1;
    if (low !== null) loads = ctx.ballots.map((b, i) => b.approvals!.includes(selected) ? low! : loads[i]);
    trace.push({round: step + 1, loadLevels: Object.fromEntries(candidates.map(c => [c, levels[c] === null ? null : asNumber(levels[c]!)])), selected, tied, loads: loads.map(asNumber)});
  }
  return result(ctx, elected, tie, trace);
}

const election: Context = {
  "method": "phragmen",
  "candidates": [
    "A",
    "B",
    "C",
    "D"
  ],
  "seats": 2,
  "ballots": [
    {
      "approvals": [
        "A",
        "B"
      ],
      "count": 6
    },
    {
      "approvals": [
        "C",
        "D"
      ],
      "count": 3
    },
    {
      "approvals": [
        "D"
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
console.log(JSON.stringify(countPhragmen(election), null, 2));
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

func CountPhragmen(request any) (map[string]any, error) {
	return run(request, "phragmen", countPhragmen)
}

func countPhragmen(x context) map[string]any {
	loads := make([]*big.Rat, len(x.ballots))
	for i := range loads {
		loads[i] = rat(0)
	}
	e := []string{}
	tr := trace{}
	tie := false
	for step := 0; step < x.seats; step++ {
		active := difference(x.c, e)
		levels := map[string]*big.Rat{}
		for _, c := range active {
			support := int64(0)
			v := rat(1)
			for i, b := range x.ballots {
				if contains(b.approvals, c) {
					support += b.count
					v = add(v, mul(loads[i], rat(b.count)))
				}
			}
			if support > 0 {
				levels[c] = div(v, rat(support))
			} else {
				levels[c] = nil
			}
		}
		tied := best(active, levels, true)
		if len(tied) == 0 {
			tied = active
		}
		winner := tied[0]
		e = append(e, winner)
		tie = tie || len(tied) > 1
		if levels[winner] != nil {
			for i, b := range x.ballots {
				if contains(b.approvals, winner) {
					loads[i] = levels[winner]
				}
			}
		}
		tr = append(tr, map[string]any{"round": step + 1, "loadLevels": numeric(levels), "selected": winner, "tied": tied, "loads": numbers(loads)})
	}
	return result(x, e, tie, tr)
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

func add(a, b *big.Rat) *big.Rat { return new(big.Rat).Add(a, b) }

func mul(a, b *big.Rat) *big.Rat { return new(big.Rat).Mul(a, b) }

func div(a, b *big.Rat) *big.Rat { return new(big.Rat).Quo(a, b) }

func number(r *big.Rat) float64 { v, _ := r.Float64(); return v }

func numeric(t map[string]*big.Rat) map[string]any {
	r := map[string]any{}
	for c, v := range t {
		if v == nil {
			r[c] = nil
		} else {
			r[c] = number(v)
		}
	}
	return r
}

func numbers(a []*big.Rat) []float64 {
	r := make([]float64, len(a))
	for i, v := range a {
		r[i] = number(v)
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

func main() {
	var request any
	if err := json.Unmarshal([]byte("{\"method\": \"phragmen\", \"seats\": 2, \"candidates\": [\"A\", \"B\", \"C\", \"D\"], \"ballots\": [{\"approvals\": [\"A\", \"B\"], \"count\": 6}, {\"approvals\": [\"C\", \"D\"], \"count\": 3}, {\"approvals\": [\"D\"], \"count\": 1}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"limit\": 1, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountPhragmen(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/python/phragmen.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/typescript/phragmen.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/go/phragmen.go) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | pass | The existing-ballot single-candidate approval monotonicity property is established for AV, PAV, seq-PAV and sequential Phragmén. This does not imply their stronger group-support property. [Source](https://arxiv.org/abs/2007.01795). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | fail | These rules satisfy single-candidate monotonicity but can lose a member of a jointly supported elected group after an existing ballot expands its approvals. The book distinguishes and documents the two properties. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | fail | Under the approval-count extension, published examples show these sequential rules can select a dominated committee; even the weaker closure-under-dominance property fails. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | fail | Under the approval-count extension, published examples show these sequential rules can select a dominated committee; even the weaker closure-under-dominance property fails. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | pass | Each round is independent of the final target size. With fixed options and tie priority, a larger committee continues the same selection sequence instead of replacing earlier members. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | conditional | For this chosen-set removal test, deleting a never-selected candidate leaves every round on the unchanged selected path and does not change represented counts or loads. This argument is specific to fixed submitted ballots and the implemented sequential tie order, not a full social-ranking IIA theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | fail | Choosing a sequence using the combined electorate can change the early reweighting or load decisions, even when the separate electorates agree on a final committee. The approval-based rule fails consistency. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | Uniform replication either multiplies all compared totals by the same positive factor, preserves harmonic objectives up to that factor, or leaves all conditional sampling shares unchanged. This concerns the selected committee or distribution, not trace numbers. [Source](https://arxiv.org/abs/1506.02891). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | not-applicable | The API receives approvals, scores or vote allocations, not complete ordinal preferences. This ranked criterion cannot be evaluated without a declared preference model; approvals are not silently converted into rankings. [Source](https://arxiv.org/abs/1506.02891). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of all approval subsets can be added across precincts and preserves the exact profile. Its worst-case size is O(2^m), which is much larger than independent candidate totals. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | pass | Sequential Phragmén satisfies PJR, which implies JR, on unrestricted approval profiles with the standard load-balancing definition. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | pass | The sequential load-balancing rule satisfies proportional justified representation; this guarantee differs from maximizing PAV’s harmonic objective. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | fail | Sequential Phragmén can distribute representation collectively without giving any single group member the ℓ approved representatives demanded by EJR. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

At most k rounds; sorting supporting ballot-group loads gives a straightforward O(kmb log b) implementation.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Lackner and Skowron: Phragmén’s rules](https://arxiv.org/abs/2007.01795)
- [abcvoting: sequential Phragmén](https://abcvoting.readthedocs.io/en/latest/abcrules.html)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
