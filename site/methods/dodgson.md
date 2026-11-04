# Dodgson’s method

Count the fewest adjacent ranking swaps needed to turn each candidate into a Condorcet winner. Prefer the smallest swap count.

**Ballot:** ranking. **API identifier:** `dodgson`.

## Counting rule

1. For a candidate, find the additional pairwise support needed against each rival.
2. Explore moving that candidate upward on individual ballots, charging one per adjacent swap.
3. Find the minimum total cost meeting every pairwise target. Compare these minimum costs across candidates.

**Variant used here:** Exact integer swaps on individual voters, not fractional swaps, an approximation, or a homogeneous variant.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

This smaller profile has three A > B > C ballots, two B > C > A ballots, and two C > B > A ballots. B already beats both rivals, so no swaps are needed. Seven voters fit the exact search limit.

```json
{
  "method": "dodgson",
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
      "count": 3
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 2
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
  "method": "dodgson",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "pairwise": {
        "A": {
          "A": 0,
          "B": 3,
          "C": 3
        },
        "B": {
          "A": 4,
          "B": 0,
          "C": 5
        },
        "C": {
          "A": 4,
          "B": 2,
          "C": 0
        }
      }
    },
    {
      "adjacentSwaps": {
        "A": 2,
        "B": 0,
        "C": 2
      }
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go requires 1.23 or newer. Replace the sample with valid input using the same format. The [API server](/api-design.md) runs Python; the Go examples count locally without a server or project imports.

<CodeSelect title="Dodgson’s method — complete algorithm">

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

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_dodgson(c, ballots, options):
    p = pairwise(c, ballots)
    rankings = [b["ranking"] for b in ballots for _ in range(b["count"])]
    threshold = len(rankings)//2 + 1
    tally = {}
    for target in c:
        opponents = [x for x in c if x != target]
        needed = tuple(max(0, threshold-p[target][x]) for x in opponents)
        states = {tuple(0 for _ in opponents): 0}
        for ranking in rankings:
            position = ranking.index(target)
            choices = []
            for swaps in range(position+1):
                passed = set(ranking[position-swaps:position])
                choices.append((swaps, tuple(int(x in passed) for x in opponents)))
            updated = {}
            for gains, cost in states.items():
                for swaps, extra in choices:
                    new = tuple(min(needed[i], gains[i]+extra[i]) for i in range(len(opponents)))
                    updated[new] = min(updated.get(new, float("inf")), cost+swaps)
            states = updated
        tally[target] = states[needed]
    return result(best(tally, True), [{"pairwise": p}, {"adjacentSwaps": tally}])

election = {'method': 'dodgson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 3}, {'ranking': ['B', 'C', 'A'], 'count': 2}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_dodgson(election["candidates"], election["ballots"], election["options"])
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

function pairwise(ctx: Context): Pairwise {
  const matrix = Object.fromEntries(ctx.candidates.map(c => [c, zeros(ctx.candidates)]));
  for (const b of ctx.ballots) for (let i = 0; i < b.ranking!.length; i++) for (let j = i + 1; j < b.ranking!.length; j++)
    matrix[b.ranking![i]][b.ranking![j]] += b.count;
  return matrix;
}

export function countDodgson(ctx: Context): SimulationResult {
  const matrix = pairwise(ctx);
  const tally = zeros(ctx.candidates);
  const rankings = ctx.ballots.flatMap(b => Array.from({length: b.count}, () => b.ranking!));
  for (const candidate of ctx.candidates) {
    const opponents = ctx.candidates.filter(c => c !== candidate);
    const need = opponents.map(c => Math.max(0, Math.floor(ctx.total / 2) + 1 - matrix[candidate][c]));
    const target = need.join(',');
    let dp = new Map<string, number>([[need.map(() => 0).join(','), 0]]);
    for (const ranking of rankings) {
      const next = new Map<string, number>();
      const pos = ranking.indexOf(candidate);
      for (const [key, cost] of dp) {
        const gained = key ? key.split(',').map(Number) : [];
        for (let promotion = 0; promotion <= pos; promotion++) {
          const crossed = ranking.slice(pos - promotion, pos);
          const updated = gained.map((v, i) => Math.min(need[i], v + (crossed.includes(opponents[i]) ? 1 : 0))).join(',');
          next.set(updated, Math.min(next.get(updated) ?? Infinity, cost + promotion));
        }
      }
      dp = next;
    }
    tally[candidate] = dp.get(target)!;
  }
  return result(ctx, best(ctx.candidates, tally, true), [{pairwise: matrix}, {adjacentSwaps: tally}]);
}

const election: Context = {
  "method": "dodgson",
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
      "count": 3
    },
    {
      "ranking": [
        "B",
        "C",
        "A"
      ],
      "count": 2
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
  "total": 7
};
console.log(JSON.stringify(countDodgson(election), null, 2));
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

func dodgson(ctx *context) map[string]any {
	p := pairwise(ctx)
	t := zeros(ctx.candidates)
	for _, target := range ctx.candidates {
		opponents := []string{}
		need := [4]int{}
		for _, x := range ctx.candidates {
			if x != target {
				need[len(opponents)] = max(0, ctx.total/2+1-int(p[target][x]))
				opponents = append(opponents, x)
			}
		}
		states := map[[4]int]int{{}: 0}
		for _, b := range ctx.ballots {
			position := 0
			for i, x := range b.ranking {
				if x == target {
					position = i
					break
				}
			}
			for voter := 0; voter < b.count; voter++ {
				updated := map[[4]int]int{}
				for gains, cost := range states {
					for swaps := 0; swaps <= position; swaps++ {
						next := gains
						for i, x := range opponents {
							if contains(b.ranking[position-swaps:position], x) {
								next[i] = min(need[i], next[i]+1)
							}
						}
						old, exists := updated[next]
						if !exists || cost+swaps < old {
							updated[next] = cost + swaps
						}
					}
				}
				states = updated
			}
		}
		t[target] = float64(states[need])
	}
	return answer(ctx, best(ctx.candidates, t, true), trace{{"pairwise": p}, {"adjacentSwaps": t}})
}

func CountDodgson(request any) (map[string]any, error) { return run(request, "dodgson", dodgson) }

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
	if err := json.Unmarshal([]byte("{\"method\": \"dodgson\", \"candidates\": [\"A\", \"B\", \"C\"], \"ballots\": [{\"ranking\": [\"A\", \"B\", \"C\"], \"count\": 3}, {\"ranking\": [\"B\", \"C\", \"A\"], \"count\": 2}, {\"ranking\": [\"C\", \"B\", \"A\"], \"count\": 2}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountDodgson(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/python/dodgson.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/typescript/dodgson.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/go/dodgson.go) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | pass | A first-place majority is protected by this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Rated majority](/criteria.md#majority-rated) | pass | A first-place majority is protected by this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Condorcet winner](/criteria.md#condorcet-winner) | pass | An existing strict head-to-head winner is selected. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Weak Pareto](/criteria.md#weak-pareto) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Strong Pareto](/criteria.md#strong-pareto) | unverified | On complete strict rankings, weak and strong Pareto have the same test. Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Monotonicity](/criteria.md#monotonicity) | fail | Extra support can change a later contest or search score so that a previous winner loses. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Consistency / reinforcement](/criteria.md#consistency) | fail | The winner in each of two electorates can lose after those electorates are combined. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Participation](/criteria.md#participation) | fail | There are profiles where joining honestly leads to a worse result than abstaining. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | fail | A previous unique winner can remain a unique winner after all rankings are reversed. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Homogeneity](/criteria.md#homogeneity) | fail | Integer swap requirements can change the winning comparison when all voters are replicated. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Polynomial counting time](/criteria.md#polynomial-time) | fail | This exact algorithm is exponential or factorial. The unrestricted winner problem is computationally hard; the small input cap is not a polynomial-time algorithm. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Resolvability](/criteria.md#resolvability) | unverified | No asymptotic tie-frequency theorem is asserted for this exact variant. A fixed priority or seed makes execution repeatable but does not prove resolvability. [Source](https://arxiv.org/abs/1804.02973). |
| [Summability](/criteria.md#summability) | pass | A histogram of all complete ranking types is additive but can contain m! entries. Small candidate totals or the original pairwise matrix generally do not capture future transfers or swap costs. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Later no harm](/criteria.md#later-no-harm) | fail | Supporting a lower preference can defeat a candidate placed above it. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [Later no help](/criteria.md#later-no-help) | fail | Adding a lower preference can improve an already higher candidate’s outcome. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf). |

## Cost and limits

Exponential search in voters and candidates; computationally difficult on unrestricted elections.

At most 5 candidates and 8 represented voters; larger inputs return HTTP 413. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Brandt: Some Remarks on Dodgson’s Voting Rule](https://pub.dss.in.tum.de/brandt-research/dodgson.pdf)
- [Handbook of Computational Social Choice](https://cgi.cse.unsw.edu.au/~haziz/comsoc.pdf)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
