# Quota Borda system (QBS)

Find groups that agree on the same top set, satisfy their proportional seat demands, and use Borda points to choose which candidates represent them.

**Ballot:** ranking. **API identifier:** `quota-borda` at `/multi/simulate`.

## Counting rule

1. Examine complete-ranking prefixes in order of increasing length. Group ballots whose unordered top-prefix sets agree.
2. Find solid coalitions whose q-PSC representation demand has not yet been met.
3. Among eligible candidates from unmet coalitions, elect a candidate with the highest global Borda total. Continue until k candidates have been selected.

**Implemented variant:** The strict-preference QBS procedure of Aziz and Lee, Algorithm 3, with q=N/(k+1)+1/(k+1)² and the published candidate priority. The quota lies above Droop’s fractional boundary and no higher than Hare.

**Ties:** The simulation chooses exactly the requested number of candidates. Earlier IDs in candidates have priority when a count needs a tied choice; later IDs are eliminated first. tie reports a consequential tied decision, not extra seats or additional elected candidates. Mathematical properties of an unbroken correspondence may require different tie assumptions. The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{
  "method": "quota-borda",
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

**The selected committee is A and C.** The exact quota is 31/9. The six A-first voters earn a seat for A. At depth two, the four voters sharing the top set C–D also earn one seat. C has more Borda points than D, so the committee is A–C.

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{
  "method": "quota-borda",
  "seats": 2,
  "winners": [
    "A",
    "C"
  ],
  "tie": false,
  "trace": [
    {
      "quota": 3.4444444444444446,
      "borda": {
        "A": 21,
        "B": 13,
        "C": 17,
        "D": 9
      }
    },
    {
      "depth": 1,
      "demands": [
        {
          "candidates": [
            "A"
          ],
          "seats": 1
        }
      ],
      "selected": "A",
      "tied": [
        "A"
      ]
    },
    {
      "depth": 2,
      "demands": [
        {
          "candidates": [
            "C",
            "D"
          ],
          "seats": 1
        }
      ],
      "selected": "C",
      "tied": [
        "C"
      ]
    }
  ]
}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go needs 1.23 or newer. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits. The server runs Python; the Go examples count locally without a server.

<CodeSelect title="Quota Borda system (QBS) — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            tally[x] += (len(c)-i-1)*b["count"]
    return tally

def droop_fraction(total, seats):
    return Fraction(total, seats+1) + Fraction(1, (seats+1)**2)

def count_quota_borda(c, ballots, seats, options):
    quota = droop_fraction(sum(b["count"] for b in ballots), seats)
    borda = borda_counts(c, ballots)
    elected, trace, tie = [], [{"quota": float(quota), "borda": borda}], False
    for depth in range(1, len(c)+1):
        groups = {}
        for b in ballots:
            prefix = tuple(x for x in c if x in b["ranking"][:depth])
            groups[prefix] = groups.get(prefix, 0)+b["count"]
        while len(elected) < seats:
            unmet = [(group, min(len(group), int(Fraction(count)/quota))) for group, count in groups.items() if sum(x in elected for x in group) < min(len(group), int(Fraction(count)/quota))]
            if not unmet:
                break
            eligible = [x for x in c if x not in elected and any(x in group for group, demand in unmet)]
            high = max(borda[x] for x in eligible)
            tied = [x for x in eligible if borda[x] == high]
            elected.append(tied[0])
            tie |= len(tied) > 1
            trace.append({"depth": depth, "demands": [{"candidates": list(group), "seats": demand} for group, demand in unmet], "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'quota-borda', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_quota_borda(election["candidates"], election["ballots"], election["seats"], election["options"])
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

function bordaCounts(ctx: Context): Tally {
  const tally = zeros(ctx.candidates);
  for (const ballot of ctx.ballots) ballot.ranking!.forEach((c, index) => {tally[c] += (ctx.candidates.length - 1 - index) * ballot.count;});
  return tally;
}

function droopFraction(total: number, seats: number): Fraction {
  return add(fraction(total, seats + 1), fraction(1, (seats + 1) ** 2));
}

export function countQuotaBorda(ctx: Context): SimulationResult {
  const quota = droopFraction(ctx.total, ctx.seats), borda = bordaCounts(ctx);
  const elected: string[] = [], trace: Trace = [{quota: asNumber(quota), borda}];
  let tie = false;
  for (let depth = 1; depth <= ctx.candidates.length; depth++) {
    const groups = new Map<string, {candidates: string[]; count: number}>();
    for (const b of ctx.ballots) {
      const prefix = ctx.candidates.filter(c => b.ranking!.slice(0, depth).includes(c));
      const key = JSON.stringify(prefix), old = groups.get(key);
      if (old) old.count += b.count; else groups.set(key, {candidates: prefix, count: b.count});
    }
    while (elected.length < ctx.seats) {
      const unmet = [...groups.values()].map(g => ({candidates: g.candidates,
        seats: Math.min(g.candidates.length, Number(BigInt(g.count) * quota[1] / quota[0]))})).filter(g => g.candidates.filter(c => elected.includes(c)).length < g.seats);
      if (!unmet.length) break;
      const eligible = ctx.candidates.filter(c => !elected.includes(c) && unmet.some(g => g.candidates.includes(c)));
      const high = Math.max(...eligible.map(c => borda[c]));
      const tied = eligible.filter(c => borda[c] === high), selected = tied[0];
      elected.push(selected); tie ||= tied.length > 1;
      trace.push({depth, demands: unmet, selected, tied});
    }
  }
  return result(ctx, elected, tie, trace);
}

const election: Context = {
  "method": "quota-borda",
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
console.log(JSON.stringify(countQuotaBorda(election), null, 2));
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

func CountQuotaBorda(request any) (map[string]any, error) {
	return run(request, "quota-borda", countQuotaBorda)
}

func countQuotaBorda(x context) map[string]any {
	q := droop(x)
	borda := borda(x)
	e := []string{}
	tie := false
	tr := trace{{"quota": number(q), "borda": numeric(borda)}}
	type group struct {
		c     []string
		count int64
	}
	for depth := 1; depth <= len(x.c); depth++ {
		groups := []group{}
		index := map[string]int{}
		for _, b := range x.ballots {
			prefix := []string{}
			for _, c := range x.c {
				if contains(b.ranking[:depth], c) {
					prefix = append(prefix, c)
				}
			}
			key := groupKey(prefix)
			if i, ok := index[key]; ok {
				groups[i].count += b.count
			} else {
				index[key] = len(groups)
				groups = append(groups, group{prefix, b.count})
			}
		}
		for len(e) < x.seats {
			unmet := []map[string]any{}
			eligible := []string{}
			for _, g := range groups {
				v := div(rat(g.count), q)
				d := int(new(big.Int).Quo(v.Num(), v.Denom()).Int64())
				if d > len(g.c) {
					d = len(g.c)
				}
				represented := 0
				for _, c := range g.c {
					if contains(e, c) {
						represented++
					}
				}
				if represented < d {
					unmet = append(unmet, map[string]any{"candidates": g.c, "seats": d})
					for _, c := range g.c {
						if !contains(e, c) && !contains(eligible, c) {
							eligible = append(eligible, c)
						}
					}
				}
			}
			if len(unmet) == 0 {
				break
			}
			ordered := []string{}
			for _, c := range x.c {
				if contains(eligible, c) {
					ordered = append(ordered, c)
				}
			}
			tied := best(ordered, borda, false)
			e = append(e, tied[0])
			tie = tie || len(tied) > 1
			tr = append(tr, map[string]any{"depth": depth, "demands": unmet, "selected": tied[0], "tied": tied})
		}
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

func frac(n, d int64) *big.Rat { return new(big.Rat).SetFrac64(n, d) }

func add(a, b *big.Rat) *big.Rat { return new(big.Rat).Add(a, b) }

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

func borda(x context) map[string]*big.Rat {
	t := zeros(x.c)
	for _, b := range x.ballots {
		for i, c := range b.ranking {
			t[c] = add(t[c], rat(int64(len(x.c)-i-1)*b.count))
		}
	}
	return t
}

func droop(x context) *big.Rat { n := int64(x.seats + 1); return add(frac(x.total, n), frac(1, n*n)) }

func groupKey(a []string) string { b, _ := json.Marshal(a); return string(b) }

func main() {
	var request any
	if err := json.Unmarshal([]byte("{\"method\": \"quota-borda\", \"seats\": 2, \"candidates\": [\"A\", \"B\", \"C\", \"D\"], \"ballots\": [{\"ranking\": [\"A\", \"B\", \"C\", \"D\"], \"count\": 6}, {\"ranking\": [\"C\", \"D\", \"A\", \"B\"], \"count\": 3}, {\"ranking\": [\"D\", \"C\", \"B\", \"A\"], \"count\": 1}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"limit\": 1, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountQuotaBorda(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/python/quota-borda.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/typescript/quota-borda.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/multi/go/quota-borda.go) program.

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
| [Proportionality for solid coalitions](/multi-criteria.md#proportionality-solid-coalitions) | pass | The stated quota lies in (N/(k+1), N/k], and the rule meets q-PSC demands on strict rankings. That entails Hare-PSC and its one-candidate solid-coalition consequence; this is not a theorem about arbitrary quota choices. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Solid coalition](/multi-criteria.md#solid-coalition) | pass | The stated quota lies in (N/(k+1), N/k], and the rule meets q-PSC demands on strict rankings. That entails Hare-PSC and its one-candidate solid-coalition consequence; this is not a theorem about arbitrary quota choices. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Candidate monotonicity](/multi-criteria.md#candidate-monotonicity) | fail | The EAR/QBS analysis distinguishes full candidate monotonicity from restricted rank-respecting improvements. Both general rules have candidate-monotonicity counterexamples for multiple seats. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Group support monotonicity](/multi-criteria.md#support-monotonicity) | not-applicable | The existing-approval-ballot group-support definition used here is not the implemented input domain. Ranked and scored support changes need their own explicit extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak Pareto](/multi-criteria.md#weak-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Strong Pareto](/multi-criteria.md#strong-pareto) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consensus committee](/multi-criteria.md#consensus-committee) | conditional | When every member of the balanced first-choice consensus set individually reaches q, its singleton coalition demands force all k members to be elected. General small-electorate cases need the quota condition; balanced first-choice counts alone are not silently assumed to reach q. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fishburn Condorcet committee](/multi-criteria.md#fishburn-condorcet) | unverified | Candidate rankings or numerical ballot entries do not by themselves specify how a voter compares entire committees. No Fishburn guarantee is claimed without choosing that extension. [Source](https://arxiv.org/abs/2007.01795). |
| [Gehrlein Condorcet committee](/multi-criteria.md#gehrlein-condorcet) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://flore.unifi.it/handle/2158/1175914). |
| [Condorcet winning set](/multi-criteria.md#condorcet-winning-set) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/1506.02891). |
| [Smith requirement for committees](/multi-criteria.md#smith) | unverified | No universal committee Smith relation is fixed for this rule. Applying the single-winner Smith set can be impossible when it has fewer members than the requested committee; a committee-graph definition must be supplied first. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Committee monotonicity](/multi-criteria.md#committee-monotonicity) | fail | The quota and representation demands change with the number of seats, so a new count can replace a previously elected candidate. Published counterexamples establish failure for the standard rule. [Source](https://arxiv.org/abs/1506.02891). |
| [Independence of irrelevant alternatives](/multi-criteria.md#iia) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Consistency](/multi-criteria.md#consistency) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Participation](/multi-criteria.md#participation) | unverified | A participation conclusion requires a preference over committees and, for random methods, lotteries. The API records candidate preferences rather than imposing that utility extension; no unconditional no-show guarantee is claimed. [Source](https://arxiv.org/abs/2007.01795). |
| [Clone independence](/multi-criteria.md#clone-independence) | unverified | A multi-seat clone definition and treatment of multiple elected copies are required. Fixed candidate priority can also distinguish exact clones; a single-winner claim is not transferred automatically. [Source](https://aso.icann.org/wp-content/uploads/2019/02/schulze2.pdf). |
| [Homogeneity](/multi-criteria.md#homogeneity) | pass | For integer group counts and ℓ≤k, reaching ℓq with q=N/(k+1)+1/(k+1)² is equivalent to a strict integer Droop demand. Replication preserves those demands, scales all Borda totals equally, and leaves fixed candidate priority unchanged. The selected committee is therefore unchanged; this argument does not apply to EAR’s fractional residual weights. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [No favorite betrayal](/multi-criteria.md#favorite-betrayal) | unverified | Sincere committee preferences and the permitted strategic ballot domain must be specified. The single-winner favorite-betrayal theorem is not automatically a theorem about k seats. [Source](https://arxiv.org/abs/2007.01795). |
| [Semi-honest strategy](/multi-criteria.md#semi-honest) | unverified | No best-response guarantee is proved for this exact committee rule, ballot domain, and tie policy. Honest-looking sample ballots do not establish a strategic existence theorem. [Source](https://arxiv.org/abs/2007.01795). |
| [Universally liked candidates](/multi-criteria.md#universally-liked) | unverified | No exact-variant guarantee or counterexample is established here. The cited definition is a starting point; a blank comparison cell is not a result. [Source](https://arxiv.org/abs/2007.01795). |
| [Weak unanimity](/multi-criteria.md#weak-unanimity) | pass | If all voters share the same unordered top-k set W, its solid coalition demands all k seats under the stated q≤N/k. The rule’s q-PSC guarantee therefore forces exactly W, independently of its members’ internal rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Strong unanimity](/multi-criteria.md#strong-unanimity) | pass | If all voters share the same unordered top-k set W, its solid coalition demands all k seats under the stated q≤N/k. The rule’s q-PSC guarantee therefore forces exactly W, independently of its members’ internal rankings. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Fixed majority](/multi-criteria.md#fixed-majority) | fail | A proportional coalition guarantee can require a seat for a substantial minority even when a strict majority shares another top-k set. For k≥3, both groups can exceed their first proportional seat threshold, contradicting a demand that every seat go to the majority’s set. [Source](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf). |
| [Polynomial counting time](/multi-criteria.md#polynomial-time) | pass | The included procedure uses polynomially many candidate, ballot-group, prefix or seat scans. Rational numerator/denominator bit growth is separate from this arithmetic-operation statement. [Source](https://arxiv.org/abs/2007.01795). |
| [Summability](/multi-criteria.md#summability) | pass | A histogram of the m! complete ranking types is sufficient and adds across precincts. This preserves transfer and prefix information but is not a compact pairwise or candidate-total summary. [Source](https://arxiv.org/abs/2007.01795). |
| [Justified representation (JR)](/multi-criteria.md#jr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Proportional justified representation (PJR)](/multi-criteria.md#pjr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |
| [Extended justified representation (EJR)](/multi-criteria.md#ejr) | not-applicable | This criterion is defined on unrestricted approval sets. The implemented ballot domain supplies different information or restricts marks; no approval threshold is inferred from scores or rankings. [Source](https://arxiv.org/abs/2007.01795). |

## Cost and limits

Polynomial prefix-group construction and repeated Borda eligibility scans; see the implementation trace for each unmet demand.

Shared limits: 32 candidates, 10,000 ballot groups and 1,000,000 represented voters; see the API guide for numeric bounds. See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

- [Aziz and Lee: QBS, Algorithm 3](https://cgi.cse.unsw.edu.au/~haziz/prsolution.pdf)

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
