# Sortition (uniform candidate lottery)

Choose a candidate uniformly, without using ballots. This comparison baseline is not a vote aggregation rule.

**Ballot:** none. **API identifier:** `sortition`.

## Counting rule

1. Require no ballots.
2. Assign each candidate probability 1 divided by the number of candidates.
3. Sample one name using the supplied seed.

**Variant used here:** Uniform lottery over submitted candidates, not a lottery over all citizens or eligible volunteers in a real civic selection process.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

There are no ballots: the candidates are A, B, and C.

```json
{
  "method": "sortition",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [],
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
  "method": "sortition",
  "winners": [
    "A"
  ],
  "tie": false,
  "trace": [
    {
      "seed": 1
    }
  ],
  "lottery": [
    {
      "candidate": "A",
      "probability": 0.3333333333333333
    },
    {
      "candidate": "B",
      "probability": 0.3333333333333333
    },
    {
      "candidate": "C",
      "probability": 0.3333333333333333
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go requires 1.23 or newer. Replace the sample with valid input using the same format. The [API server](/api-design.md) runs Python; the Go examples count locally without a server or project imports.

<CodeSelect title="Sortition (uniform candidate lottery) — complete algorithm">

```python
# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def count_sortition(c, ballots, options):
    lottery = [{"candidate": x, "probability": 1/len(c)} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"seed": options["seed"]}], lottery=lottery)

election = {'method': 'sortition', 'candidates': ['A', 'B', 'C'], 'ballots': [], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_sortition(election["candidates"], election["ballots"], election["options"])
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

export function countSortition(ctx: Context): SimulationResult {
  const probabilities = ctx.candidates.map(() => 1 / ctx.candidates.length);
  const chosen = sample(probabilities, ctx.seed);
  return result(ctx, [ctx.candidates[chosen]], [{seed: ctx.seed}], probabilities);
}

const election: Context = {
  "method": "sortition",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 0
};
console.log(JSON.stringify(countSortition(election), null, 2));
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

type trace []map[string]any

func answer(ctx *context, w []string, tr trace) map[string]any {
	ordered := []string{}
	for _, c := range ctx.candidates {
		if contains(w, c) {
			ordered = append(ordered, c)
		}
	}
	return map[string]any{"method": ctx.method, "winners": ordered, "tie": len(ordered) > 1, "trace": tr}
}

func sample(ctx *context, prob []float64, tr trace) map[string]any {
	threshold := float64(ctx.seed*1664525+1013904223) / 4294967296
	sum := float64(0)
	chosen := len(prob) - 1
	lottery := make([]map[string]any, len(prob))
	for i, p := range prob {
		lottery[i] = map[string]any{"candidate": ctx.candidates[i], "probability": p}
	}
	for i, p := range prob {
		sum += p
		if threshold < sum {
			chosen = i
			break
		}
	}
	out := answer(ctx, []string{ctx.candidates[chosen]}, tr)
	out["lottery"] = lottery
	return out
}

func sortition(ctx *context) map[string]any {
	p := make([]float64, len(ctx.candidates))
	for i := range p {
		p[i] = 1 / float64(len(p))
	}
	return sample(ctx, p, trace{{"seed": ctx.seed}})
}

func CountSortition(request any) (map[string]any, error) { return run(request, "sortition", sortition) }

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
	if err := json.Unmarshal([]byte("{\"method\": \"sortition\", \"candidates\": [\"A\", \"B\", \"C\"], \"ballots\": [], \"options\": {\"maxScore\": 5, \"budget\": 100, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountSortition(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/python/sortition.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/typescript/sortition.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/go/sortition.go) file. The complete engines use the same functions.

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
| [Weak Pareto](/criteria.md#weak-pareto) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. A dominated alternative can share the best total or receive positive lottery probability. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Strong Pareto](/criteria.md#strong-pareto) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. A dominated alternative can share the best total or receive positive lottery probability. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Smith set](/criteria.md#smith) | fail | Here winning guarantees mean probability one and exclusions mean probability zero. The rule can elect outside the smallest strictly majority-dominant set. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Smith independence](/criteria.md#smith-iia) | not-applicable | No preferences are collected, so no Smith set is defined for the submitted data. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | fail | Assess the lottery distribution, not the winner sampled with a fixed seed. A dominated candidate can change point gaps, victories or elimination decisions among others. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | conditional | Deleting candidates leaves the relative probability ratio between two retained candidates unchanged, but changes their absolute probabilities. This is a lottery interpretation, not deterministic winner IIA. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Assess the lottery distribution, not the winner sampled with a fixed seed. Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Monotonicity](/criteria.md#monotonicity) | pass | Assess the lottery distribution, not the winner sampled with a fixed seed. Increasing support for a winning candidate cannot reduce that candidate’s winning status under the stated rule. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Consistency / reinforcement](/criteria.md#consistency) | not-applicable | Assess the lottery distribution, not the winner sampled with a fixed seed. This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Participation](/criteria.md#participation) | not-applicable | No ballot is accepted, so there is no honest participation operation. Candidate entry changes the sampling universe instead. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | not-applicable | This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Homogeneity](/criteria.md#homogeneity) | not-applicable | Assess the lottery distribution, not the winner sampled with a fixed seed. This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(m) to construct and report the lottery. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Resolvability](/criteria.md#resolvability) | not-applicable | Randomness is part of the outcome rule, not merely a device for resolving exact counting ties. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Summability](/criteria.md#summability) | not-applicable | No vote summary is needed; the candidate list determines the uniform lottery. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Later no harm](/criteria.md#later-no-harm) | not-applicable | The simulation accepts no ballots or preferences. There is no ballot operation or strategic report to compare; the candidate list alone defines the lottery. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [Later no help](/criteria.md#later-no-help) | not-applicable | The simulation accepts no ballots or preferences. There is no ballot operation or strategic report to compare; the candidate list alone defines the lottery. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | not-applicable | The simulation accepts no ballots or preferences. There is no ballot operation or strategic report to compare; the candidate list alone defines the lottery. [Source](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html). |

## Cost and limits

O(m) to construct and report the lottery.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Probabilistic methods — Preferential Voting Tools](https://pref-voting.readthedocs.io/en/stable/probabilistic_methods.html)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
