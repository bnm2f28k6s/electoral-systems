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
