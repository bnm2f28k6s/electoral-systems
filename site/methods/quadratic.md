# Quadratic voting (credit budget)

A voter may cast multiple signed voice votes, paying the square of each amount from a fixed personal budget. Sum voice votes to select the winner.

**Ballot:** credits. **API identifier:** `quadratic`.

## Counting rule

1. For each ballot require integer voice amounts for all candidates.
2. Check that the sum of squared amounts is at most the declared budget.
3. Add signed voice votes per candidate and return the largest total.

**Variant used here:** Equal, nontransferable per-voter credit budget; credits fields contain voice votes v, whose cost is v². This is a teaching extension to multiple candidates, not the original binary money-purchase model.

**Ties:** Final equal best candidates are returned together. When a stage needs a single choice, the earlier candidate in the submitted candidates array has priority; this is part of the simulation, not a claim about every implementation. See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.

```json
{
  "method": "quadratic",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "credits": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 5
      },
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
  "method": "quadratic",
  "winners": [
    "B"
  ],
  "tie": false,
  "trace": [
    {
      "tally": {
        "A": 20,
        "B": 32,
        "C": 19
      },
      "budget": 100
    }
  ]
}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go requires 1.23 or newer. Replace the sample with valid input using the same format. The [API server](/api-design.md) runs Python; the Go examples count locally without a server or project imports.

<CodeSelect title="Quadratic voting (credit budget) — complete algorithm">

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

def count_quadratic(c, ballots, options):
    # credits records signed voice votes; the budget charges their squares.
    tally = {x: sum(b["credits"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally, "budget": options["budget"]}])

election = {'method': 'quadratic', 'candidates': ['A', 'B', 'C'], 'ballots': [{'credits': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'credits': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'credits': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_quadratic(election["candidates"], election["ballots"], election["options"])
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

export function countQuadratic(ctx: Context): SimulationResult {
  const tally = zeros(ctx.candidates);
  for (const b of ctx.ballots) for (const c of ctx.candidates) tally[c] += b.credits![c] * b.count;
  return result(ctx, best(ctx.candidates, tally), [{tally, budget: ctx.budget}]);
}

const election: Context = {
  "method": "quadratic",
  "candidates": [
    "A",
    "B",
    "C"
  ],
  "ballots": [
    {
      "credits": {
        "A": 5,
        "B": 3,
        "C": 0
      },
      "count": 4
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 3
      },
      "count": 3
    },
    {
      "credits": {
        "A": 0,
        "B": 4,
        "C": 5
      },
      "count": 2
    }
  ],
  "maxScore": 5,
  "budget": 100,
  "seed": 1,
  "total": 9
};
console.log(JSON.stringify(countQuadratic(election), null, 2));
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

func scoreCounts(ctx *context) tally {
	t := zeros(ctx.candidates)
	for _, b := range ctx.ballots {
		for _, s := range ctx.candidates {
			t[s] += float64(b.values[s] * b.count)
		}
	}
	return t
}

func quadratic(ctx *context) map[string]any {
	t := scoreCounts(ctx)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t, "budget": ctx.budget}})
}

func CountQuadratic(request any) (map[string]any, error) { return run(request, "quadratic", quadratic) }

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
	if err := json.Unmarshal([]byte("{\"method\": \"quadratic\", \"candidates\": [\"A\", \"B\", \"C\"], \"ballots\": [{\"credits\": {\"A\": 5, \"B\": 3, \"C\": 0}, \"count\": 4}, {\"credits\": {\"A\": 0, \"B\": 4, \"C\": 3}, \"count\": 3}, {\"credits\": {\"A\": 0, \"B\": 4, \"C\": 5}, \"count\": 2}], \"options\": {\"maxScore\": 5, \"budget\": 100, \"seed\": 1}}"), &request); err != nil {
		panic(err)
	}
	answer, err := CountQuadratic(request)
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

Download the standalone [Python](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/python/quadratic.py), [TypeScript](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/typescript/quadratic.ts), or [Go](https://github.com/bnm2f28k6s/electoral-systems/blob/main/examples/go/quadratic.go) file. The complete engines use the same functions.

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
| [Ranked majority](/criteria.md#majority-ranked) | fail | Having a first-place majority does not force the largest total, survival, or probability one. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Rated majority](/criteria.md#majority-rated) | not-applicable | A voice-credit budget is not an independent bounded grade for each candidate; the cost constraint couples the amounts. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Majority loser](/criteria.md#majority-loser) | fail | A candidate ranked last by a majority can still win; intensity, position totals, or a random draw can override that fact. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Mutual majority](/criteria.md#mutual-majority) | fail | Agreement by a majority on a group does not ensure this rule elects from that group. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Condorcet winner](/criteria.md#condorcet-winner) | fail | This rule can select somebody who loses a head-to-head contest to another candidate. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Condorcet loser](/criteria.md#condorcet-loser) | fail | Losing every pairwise comparison does not always prevent winning under this rule. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Weak Pareto](/criteria.md#weak-pareto) | conditional | If every submitted signed voice value for A exceeds B’s value, A’s sum exceeds B’s. Unexpressed preferences need not follow the constrained voice allocation. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Strong Pareto](/criteria.md#strong-pareto) | conditional | If A’s submitted voice value is at least B’s on every ballot and greater on one, A’s sum is greater. This is submitted-value dominance. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Smith set](/criteria.md#smith) | fail | The rule can elect outside the smallest strictly majority-dominant set. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Smith independence](/criteria.md#smith-iia) | fail | Removing outsiders can alter the tally or elimination path and thus the winner. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of Pareto-dominated alternatives](/criteria.md#ipda) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of irrelevant alternatives](/criteria.md#iia) | fail | Removing a losing candidate can change which of the remaining candidates wins. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Local independence of irrelevant alternatives](/criteria.md#liia) | unverified | The API reports winners, not a complete social ordering. No LIIA guarantee is asserted for a recursively induced ranking. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Independence of clones](/criteria.md#clone-independence) | fail | Splitting a candidate into adjacent clones can change the winning group or an outsider’s status. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Monotonicity](/criteria.md#monotonicity) | conditional | Increasing only A’s voice amount increases A’s total when the changed ballot still satisfies its credit budget; spending more on A may otherwise require reducing other amounts. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Consistency / reinforcement](/criteria.md#consistency) | pass | For additive totals, positive winning margins in separate groups stay positive when the totals are added. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Participation](/criteria.md#participation) | conditional | Summing signed voices is additive, but strategic credit allocation and preference comparisons require a model beyond simple rankings. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Reversal symmetry](/criteria.md#reversal-symmetry) | unverified | Not established here for this exact variant and tie policy. A blank source-table cell is not evidence of either passing or failing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Homogeneity](/criteria.md#homogeneity) | pass | Scaling every ballot count equally preserves the decisive comparisons or probabilities. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Polynomial counting time](/criteria.md#polynomial-time) | pass | O(bm) tally and budget validation. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Resolvability](/criteria.md#resolvability) | conditional | Under a nondegenerate large-electorate model, exact equal decisive totals are typically rare. No universal tie-frequency claim is made without a probability model; fixed priority alone proves nothing. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Summability](/criteria.md#summability) | pass | O(m) candidate totals are additive; random ballot also needs the electorate total. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Later no harm](/criteria.md#later-no-harm) | not-applicable | This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [Later no help](/criteria.md#later-no-help) | not-applicable | This ballot or outcome model does not provide the operation in the criterion’s definition. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |
| [No favorite betrayal](/criteria.md#favorite-betrayal) | fail | Some profiles give an incentive to put a compromise strictly above the voter’s favorite. [Source](https://bfi.uchicago.edu/working-paper/quadratic-voting/). |

## Cost and limits

O(bm) tally and budget validation.

See the API guide for shared input limits. The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

- [Lalley and Weyl: Quadratic Voting](https://bfi.uchicago.edu/working-paper/quadratic-voting/)

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
