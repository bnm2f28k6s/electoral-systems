# Nanson’s method

Repeatedly remove candidates whose Borda points are at or below the current average.

**Ballot:** ranking. **API identifier:** `nanson`.

## Counting rule

1. With k candidates left, assign k−1 points to first place down to zero for last.
2. Recompute the average candidate total and eliminate all candidates at or below it.
3. Repeat; if every remaining candidate has the same total, return their tie.

**Variant used here:** Non-strict Nanson: eliminate at or below the average, rather than only below it.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "nanson",
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

The result is **B**. The trace records intermediate totals, eliminations, comparisons, or the lottery used by this rule.

```json
{
  "method": "nanson",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "active": [
        "A",
        "B",
        "C"
      ],
      "tally": {
        "A": 8,
        "B": 12,
        "C": 7
      },
      "eliminated": [
        "A",
        "C"
      ]
    },
    {
      "active": [
        "B"
      ]
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go requires 1.23 or newer. Replace the sample with valid input using the same format. The [API server](/api-design.md) runs Python; the Go examples count locally without a server or project imports.

<CodeSelect title="Nanson’s method — complete algorithm">

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

def first_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        choice = b.get("choice") or next(x for x in b["ranking"] if x in active)
        tally[choice] += b["count"]
    return tally

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        ranking = [x for x in b["ranking"] if x in active]
        for position, x in enumerate(ranking):
            tally[x] += (len(c) - position - 1) * b["count"]
    return tally

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def smith_set(c, p):
    # Closure adds every outsider not strictly beaten by each current member.
    closures = []
    for start in c:
        group = {start}
        while True:
            expanded = group | {y for y in c if any(p[x][y] <= p[y][x] for x in group if x != y)}
            if expanded == group:
                break
            group = expanded
        closures.append(group)
    smallest = min(closures, key=len)
    return [x for x in c if x in smallest]

def elimination(c, ballots, mode):
    active = c[:]
    trace = []
    total = sum(b["count"] for b in ballots)
    p = pairwise(c, ballots) if mode == "tideman-alternative" else None
    while len(active) > 1:
        if p is not None:
            smith = smith_set(active, p)
            if smith != active:
                trace.append({"active": active[:], "smith": smith})
                active = smith
                if len(active) == 1:
                    break
        first = first_counts(active, ballots)
        if mode in {"instant-runoff", "coombs", "tideman-alternative"}:
            majority = [x for x in active if first[x]*2 > total]
            if majority:
                trace.append({"active": active[:], "tally": first})
                return result(majority, trace)
        if mode == "coombs":
            tally = dict.fromkeys(active, 0)
            for b in ballots:
                last = next(x for x in reversed(b["ranking"]) if x in tally)
                tally[last] += b["count"]
            worst = best(tally)
        elif mode in {"nanson", "baldwin"}:
            tally = borda_counts(active, ballots)
            worst = best(tally, True)
        else:
            tally = first
            worst = best(tally, True)
        row = {"active": active[:], "tally": tally}
        if len(set(tally.values())) == 1 and (mode == "nanson" or len(active) == 2):
            trace.append(row)
            return result(active, trace)
        if mode == "nanson":
            eliminated = [x for x in active if tally[x]*len(active) <= sum(tally.values())]
        else:
            eliminated = [worst[-1]]
        row["eliminated"] = eliminated
        trace.append(row)
        active = [x for x in active if x not in eliminated]
    trace.append({"active": active[:]})
    return result(active, trace)

def count_nanson(c, ballots, options):
    return elimination(c, ballots, "nanson")

election = {'method': 'nanson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_nanson(election["candidates"], election["ballots"], election["options"])
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

function firstCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) tally[b.ranking!.find(c => active.includes(c))!] += b.count;
  return tally;
}

function bordaCounts(ctx: Context, active: string[]): Tally {
  const tally = zeros(active);
  for (const b of ctx.ballots) {
    const order = b.ranking!.filter(c => active.includes(c));
    order.forEach((c, i) => { tally[c] += (active.length - 1 - i) * b.count; });
  }
  return tally;
}

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

function smith(active: string[], matrix: Pairwise): string[] {
  let smallest = active;
  for (const start of active) {
    const set = new Set([start]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const d of active) if (!set.has(d) && [...set].some(c => matrix[c][d] <= matrix[d][c])) { set.add(d); changed = true; }
    }
    if (set.size < smallest.length) smallest = active.filter(c => set.has(c));
  }
  return smallest;
}

function elimination(ctx: Context, mode: string): SimulationResult {
  let active = [...ctx.candidates];
  const trace: Trace = [];
  const matrix = mode === 'tideman-alternative' ? pairwise(ctx) : null;
  while (active.length > 1) {
    if (matrix) {
      const smithSet = smith(active, matrix);
      if (smithSet.length !== active.length) {
        trace.push({active: [...active], smith: smithSet});
        active = smithSet;
        if (active.length === 1) break;
      }
    }
    const first = firstCounts(ctx, active);
    if (['instant-runoff', 'coombs', 'tideman-alternative'].includes(mode)) {
      const majority = active.filter(c => first[c] * 2 > ctx.total);
      if (majority.length) { trace.push({active: [...active], tally: first}); return result(ctx, majority, trace); }
    }
    let tally = first;
    let worst: string[];
    if (mode === 'coombs') {
      tally = zeros(active);
      for (const b of ctx.ballots) tally[b.ranking!.filter(c => active.includes(c)).at(-1)!] += b.count;
      worst = best(active, tally);
    } else if (['nanson', 'baldwin'].includes(mode)) {
      tally = bordaCounts(ctx, active);
      worst = best(active, tally, true);
    } else worst = best(active, tally, true);
    const row: Record<string, unknown> = {active: [...active], tally};
    if (new Set(Object.values(tally)).size === 1 && (mode === 'nanson' || active.length === 2)) { trace.push(row); return result(ctx, active, trace); }
    const eliminated = mode === 'nanson'
      ? active.filter(c => tally[c] * active.length <= Object.values(tally).reduce((a, b) => a + b, 0))
      : [worst.at(-1)!];
    row.eliminated = eliminated;
    trace.push(row);
    active = active.filter(c => !eliminated.includes(c));
  }
  trace.push({active: [...active]});
  return result(ctx, active, trace);
}

export function countNanson(ctx: Context): SimulationResult { return elimination(ctx, 'nanson'); }

function gcd(a: bigint, b: bigint): bigint { while (b) { const t = b; b = a % b; a = t; } return a < 0n ? -a : a; }

function fraction(n: bigint, d = 1n): Fraction { if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d); return [n / g, d / g]; }

function add(a: Fraction, b: Fraction): Fraction { return fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1]); }

const election: Context = {
  "method": "nanson",
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
console.log(JSON.stringify(countNanson(election), null, 2));
```

```go
// Go 1.23+. Save as example.go and run: go run example.go
// Self-contained count, extracted from the validated Go engine.
package main

import (
	json "encoding/json"
	fmt "fmt"
	math "math"
	os "os"
	strings "strings"
	unicode "unicode"
	utf8 "unicode/utf8"
)

type tally map[string]float64

type trace []map[string]any

func zeros(c []string) tally {
	t := tally{}
	for _, s := range c {
		t[s] = 0
	}
	return t
}

func best(c []string, t tally, minimum bool) []string {
	out := []string{}
	v := t[c[0]]
	for _, s := range c {
		if (!minimum && t[s] > v) || (minimum && t[s] < v) {
			v = t[s]
		}
	}
	for _, s := range c {
		if t[s] == v {
			out = append(out, s)
		}
	}
	return out
}

func answer(ctx *context, w []string, tr trace) map[string]any {
	ordered := []string{}
	for _, c := range ctx.candidates {
		if contains(w, c) {
			ordered = append(ordered, c)
		}
	}
	return map[string]any{"method": ctx.method, "winners": ordered, "tie": len(ordered) > 1, "trace": tr}
}

func firstCounts(ctx *context, c []string) tally {
	t := zeros(c)
	for _, b := range ctx.ballots {
		if b.hasChoice {
			t[b.choice] += float64(b.count)
		} else {
			for _, s := range b.ranking {
				if contains(c, s) {
					t[s] += float64(b.count)
					break
				}
			}
		}
	}
	return t
}

func bordaCounts(ctx *context, c []string) tally {
	t := zeros(c)
	for _, b := range ctx.ballots {
		i := 0
		for _, s := range b.ranking {
			if contains(c, s) {
				t[s] += float64((len(c) - i - 1) * b.count)
				i++
			}
		}
	}
	return t
}

func pairwise(ctx *context) map[string]tally {
	p := map[string]tally{}
	for _, s := range ctx.candidates {
		p[s] = zeros(ctx.candidates)
	}
	for _, b := range ctx.ballots {
		for i, x := range b.ranking {
			for _, y := range b.ranking[i+1:] {
				p[x][y] += float64(b.count)
			}
		}
	}
	return p
}

func smith(c []string, p map[string]tally) []string {
	smallest := c
	for _, start := range c {
		group := map[string]bool{start: true}
		for {
			changed := false
			for _, y := range c {
				if !group[y] {
					for _, x := range c {
						if group[x] && p[x][y] <= p[y][x] {
							group[y] = true
							changed = true
							break
						}
					}
				}
			}
			if !changed {
				break
			}
		}
		if len(group) < len(smallest) {
			smallest = []string{}
			for _, x := range c {
				if group[x] {
					smallest = append(smallest, x)
				}
			}
		}
	}
	return smallest
}

func elimination(ctx *context, mode string) map[string]any {
	active := append([]string{}, ctx.candidates...)
	tr := trace{}
	var p map[string]tally
	if mode == "tideman-alternative" {
		p = pairwise(ctx)
	}
	for len(active) > 1 {
		if p != nil {
			s := smith(active, p)
			if len(s) != len(active) {
				tr = append(tr, map[string]any{"active": active, "smith": s})
				active = s
				if len(active) == 1 {
					break
				}
			}
		}
		first := firstCounts(ctx, active)
		if mode == "instant-runoff" || mode == "coombs" || mode == "tideman-alternative" {
			w := []string{}
			for _, s := range active {
				if first[s]*2 > float64(ctx.total) {
					w = append(w, s)
				}
			}
			if len(w) > 0 {
				return answer(ctx, w, append(tr, map[string]any{"active": active, "tally": first}))
			}
		}
		t := first
		minimum := true
		if mode == "coombs" {
			t = zeros(active)
			minimum = false
			for _, b := range ctx.ballots {
				for i := len(b.ranking) - 1; i >= 0; i-- {
					if contains(active, b.ranking[i]) {
						t[b.ranking[i]] += float64(b.count)
						break
					}
				}
			}
		} else if mode == "nanson" || mode == "baldwin" {
			t = bordaCounts(ctx, active)
		}
		worst := best(active, t, minimum)
		row := map[string]any{"active": active, "tally": t}
		equal := true
		sum := float64(0)
		for _, s := range active {
			sum += t[s]
			if t[s] != t[active[0]] {
				equal = false
			}
		}
		if equal && (mode == "nanson" || len(active) == 2) {
			return answer(ctx, active, append(tr, row))
		}
		removed := []string{worst[len(worst)-1]}
		if mode == "nanson" {
			removed = []string{}
			for _, s := range active {
				if t[s]*float64(len(active)) <= sum {
					removed = append(removed, s)
				}
			}
		}
		row["eliminated"] = removed
		tr = append(tr, row)
		next := []string{}
		for _, s := range active {
			if !contains(removed, s) {
				next = append(next, s)
			}
		}
		active = next
	}
	return answer(ctx, active, append(tr, map[string]any{"active": active}))
}

func nanson(ctx *context) map[string]any { return elimination(ctx, "nanson") }

func CountNanson(request any) (map[string]any, error) { return run(request, "nanson", nanson) }

type ElectionError struct {
	Status  int
	Message string
}

func (e *ElectionError) Error() string { return e.Message }

func invalid(message string) error { return &ElectionError{400, message} }

func limit(message string) error { return &ElectionError{413, message} }

type ballot struct {
	ranking   []string
	choice    string
	hasChoice bool
	approvals []string
	values    map[string]int
	count     int
}

type context struct {
	method                  string
	candidates              []string
	ballots                 []ballot
	maxScore, budget, total int
	seed                    uint32
}

func knownMethod(s string) bool {
	switch s {
	case "plurality", "anti-plurality", "two-round", "instant-runoff", "coombs", "nanson", "baldwin", "tideman-alternative", "minimax", "copeland", "black", "kemeny-young", "ranked-pairs", "schulze", "borda", "bucklin", "dodgson", "approval", "majority-judgment", "score", "star", "quadratic", "random-ballot", "maximal-lotteries", "sortition":
		return true
	}
	return false
}

func exactKeys(m map[string]any, keys ...string) bool {
	for k := range m {
		if !contains(keys, k) {
			return false
		}
	}
	return true
}

func contains(a []string, s string) bool {
	for _, v := range a {
		if v == s {
			return true
		}
	}
	return false
}

func number(v any) (int64, bool) {
	var f float64
	switch n := v.(type) {
	case float64:
		f = n
	case float32:
		f = float64(n)
	case int:
		f = float64(n)
	case int64:
		f = float64(n)
	case int32:
		f = float64(n)
	case uint:
		f = float64(n)
	case uint64:
		f = float64(n)
	case json.Number:
		var err error
		f, err = n.Float64()
		if err != nil {
			return 0, false
		}
	default:
		return 0, false
	}
	if math.IsNaN(f) || math.IsInf(f, 0) || math.Abs(f) > 9007199254740991 || math.Trunc(f) != f {
		return 0, false
	}
	return int64(f), true
}

func stringArray(v any) ([]string, bool) {
	a, ok := v.([]any)
	if !ok {
		return nil, false
	}
	out := make([]string, 0, len(a))
	for _, x := range a {
		s, ok := x.(string)
		if !ok {
			return nil, false
		}
		out = append(out, s)
	}
	return out, true
}

func validate(request any) (*context, error) {
	r, ok := request.(map[string]any)
	if !ok || r == nil {
		return nil, invalid("Request must be an object")
	}
	if !exactKeys(r, "method", "candidates", "ballots", "options") {
		return nil, invalid("Unknown request field")
	}
	method, ok := r["method"].(string)
	if !ok || !knownMethod(method) {
		return nil, invalid("Unknown method")
	}
	c, ok := stringArray(r["candidates"])
	if !ok || len(c) == 0 {
		return nil, invalid("Supply at least one candidate")
	}
	if len(c) > 32 {
		return nil, limit("At most 32 candidates")
	}
	seen := map[string]bool{}
	for _, s := range c {
		if strings.TrimFunc(s, func(r rune) bool { return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f) }) == "" || utf8.RuneCountInString(s) > 100 {
			return nil, invalid("Candidate IDs must be nonempty strings of at most 100 characters")
		}
		if seen[s] {
			return nil, invalid("Candidate IDs must be unique")
		}
		seen[s] = true
	}
	opts := map[string]any{}
	if v, exists := r["options"]; exists {
		opts, ok = v.(map[string]any)
		if !ok || opts == nil {
			return nil, invalid("options must be an object")
		}
	}
	if !exactKeys(opts, "maxScore", "budget", "seed") {
		return nil, invalid("Unknown option")
	}
	ctx := &context{method: method, candidates: c, maxScore: 5, budget: 100, seed: 1, ballots: []ballot{}}
	for _, o := range []struct {
		name   string
		lo, hi int64
	}{{"maxScore", 1, 100}, {"budget", 1, 1000000}, {"seed", 0, 4294967295}} {
		if v, exists := opts[o.name]; exists {
			n, valid := number(v)
			if !valid || n < o.lo || n > o.hi {
				return nil, invalid(fmt.Sprintf("%s must be an integer from %d to %d", o.name, o.lo, o.hi))
			}
			switch o.name {
			case "maxScore":
				ctx.maxScore = int(n)
			case "budget":
				ctx.budget = int(n)
			case "seed":
				ctx.seed = uint32(n)
			}
		}
	}
	bs, ok := r["ballots"].([]any)
	if !ok {
		return nil, invalid("ballots must be an array")
	}
	if len(bs) > 10000 {
		return nil, limit("At most 10000 ballot groups")
	}
	if method == "sortition" && len(bs) != 0 {
		return nil, invalid("Sortition accepts no ballots")
	}
	if method != "sortition" && len(bs) == 0 {
		return nil, invalid("At least one ballot is required")
	}
	for _, raw := range bs {
		b, ok := raw.(map[string]any)
		if !ok || b == nil {
			return nil, invalid("Each ballot must be an object")
		}
		if !exactKeys(b, "ranking", "choice", "approvals", "scores", "credits", "count") {
			return nil, invalid("Unknown ballot field")
		}
		field := ""
		for _, k := range []string{"ranking", "choice", "approvals", "scores", "credits"} {
			if _, exists := b[k]; exists {
				if field != "" {
					return nil, invalid("Each ballot needs exactly one ballot format")
				}
				field = k
			}
		}
		if field == "" {
			return nil, invalid("Each ballot needs exactly one ballot format")
		}
		n := int64(1)
		if v, exists := b["count"]; exists {
			n, ok = number(v)
			if !ok || n < 1 || n > 1000000 {
				return nil, invalid("count must be a positive integer at most 1000000")
			}
		}
		ctx.total += int(n)
		if ctx.total > 1000000 {
			return nil, limit("At most 1000000 represented voters")
		}
		expected := "ranking"
		switch method {
		case "approval":
			expected = "approvals"
		case "score", "star", "majority-judgment":
			expected = "scores"
		case "quadratic":
			expected = "credits"
		}
		allowed := field == expected
		if method == "plurality" || method == "anti-plurality" || method == "random-ballot" {
			allowed = field == "ranking" || field == "choice"
		}
		if !allowed {
			return nil, invalid("Wrong ballot format for " + method)
		}
		out := ballot{count: int(n)}
		switch field {
		case "ranking", "approvals":
			a, valid := stringArray(b[field])
			used := map[string]bool{}
			if !valid {
				return nil, invalid(field + " must be an array of candidates")
			}
			for _, s := range a {
				if !seen[s] || used[s] {
					return nil, invalid(field + " must contain distinct candidates")
				}
				used[s] = true
			}
			if field == "ranking" {
				if len(a) != len(c) {
					return nil, invalid("ranking must list every candidate exactly once")
				}
				out.ranking = a
			} else {
				out.approvals = a
			}
		case "choice":
			s, valid := b[field].(string)
			if !valid || !seen[s] {
				return nil, invalid("choice must name a candidate")
			}
			out.choice = s
			out.hasChoice = true
		default:
			values, valid := b[field].(map[string]any)
			if !valid || len(values) != len(c) {
				return nil, invalid(field + " must contain every candidate exactly once")
			}
			out.values = map[string]int{}
			squares := float64(0)
			for _, s := range c {
				v, exists := values[s]
				x, valid := number(v)
				if !exists || !valid {
					return nil, invalid(field + " values must be safe integers")
				}
				if field == "scores" && (x < 0 || x > int64(ctx.maxScore)) {
					return nil, invalid("Scores outside 0..maxScore")
				}
				squares += float64(x) * float64(x)
				if field == "credits" && squares > float64(ctx.budget) {
					return nil, invalid("Quadratic ballot exceeds sum-of-squares budget")
				}
				out.values[s] = int(x)
			}
		}
		ctx.ballots = append(ctx.ballots, out)
	}
	if method == "kemeny-young" && len(c) > 8 {
		return nil, limit("Exact Kemeny enumeration supports at most 8 candidates")
	}
	if method == "dodgson" && (len(c) > 5 || ctx.total > 8) {
		return nil, limit("Exact Dodgson supports at most 5 candidates and 8 represented voters")
	}
	if method == "maximal-lotteries" && len(c) > 6 {
		return nil, limit("Exact maximal-lottery vertex enumeration supports at most 6 candidates")
	}
	return ctx, nil
}

func run(request any, method string, count func(*context) map[string]any) (map[string]any, error) {
	ctx, err := validate(request)
	if err != nil {
		return nil, err
	}
	if ctx.method != method {
		return nil, invalid("Expected method " + method)
	}
	return count(ctx), nil
}

func main() {
	var request any
	if err := json.Unmarshal([]byte("{\"method\": \"nanson\", \"candidates\": [\"A\", \"B\", \"C\"], \"ballots\": [{\"ranking\": [\"A\", \"B\", \"C\"], \"count\": 4}, {\"ranking\": [\"B\", \"C\", \"A\"], \"count\": 3}, {\"ranking\": [\"C\", \"B\", \"A\"], \"count\": 2}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountNanson(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/python/nanson.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/typescript/nanson.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/go/nanson.go) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Majority loser](/criteria.md#majority-loser) | pass | A strict last-place majority prevents election under the standard rule. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Mutual majority](/criteria.md#mutual-majority) | pass | A majority agreeing on a preferred group keeps the winner within that group. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Condorcet loser](/criteria.md#condorcet-loser) | pass | The standard rule excludes a candidate losing every pairwise comparison. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Weak Pareto](/criteria.md#weak-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | pass | On this complete strict-ranking domain, unanimous A above B protects A over B; the comparison concerns the mathematical rule before any external final tie resolution. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Smith set](/criteria.md#smith) | pass | The standard rule chooses only from the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Monotonicity](/criteria.md#monotonicity) | fail | Extra support can change a later contest or search score so that a previous winner loses. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | conditional | The usual rule is reported reversal symmetric, but consequential equal elimination totals and a fixed external priority must be treated explicitly. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | At most m rounds; O(bm²). [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Summability](/criteria.md#summability) | pass | O(m²) original pairwise counts suffice; two-round also needs O(m) first-choice totals. For Nanson and Baldwin, restricted Borda points equal the sum of pairwise support against remaining rivals. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html). |

## Cost and limits

At most m rounds; O(bm²).

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Iterative methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/iterative_methods.html)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
