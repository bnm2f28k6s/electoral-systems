package multi

import "math/big"

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
func indexOf(a []string, s string) int {
	for i, c := range a {
		if c == s {
			return i
		}
	}
	return -1
}
func schulzeStrength(x context, committee []string, outsider string) *big.Rat {
	var strength *big.Rat
	for size := 1; size <= len(committee); size++ {
		for _, subset := range combinations(committee, size) {
			support := int64(0)
			for _, b := range x.ballots {
				for _, c := range subset {
					if indexOf(b.ranking, c) < indexOf(b.ranking, outsider) {
						support += b.count
						break
					}
				}
			}
			v := frac(support, int64(size))
			if strength == nil || v.Cmp(strength) < 0 {
				strength = v
			}
		}
	}
	return strength
}
func countSchulzeStv(x context) map[string]any {
	cs := combinations(x.c, x.seats)
	n := len(cs)
	links := ratMatrix(n)
	paths := ratMatrix(n)
	for i, first := range cs {
		for j, second := range cs {
			outside := difference(second, first)
			if len(outside) == 1 {
				links[i][j] = schulzeStrength(x, first, outside[0])
			}
			paths[i][j] = links[i][j]
		}
	}
	for middle := 0; middle < n; middle++ {
		for start := 0; start < n; start++ {
			for end := 0; end < n; end++ {
				if middle != start && middle != end && start != end {
					v := paths[start][middle]
					if paths[middle][end].Cmp(v) < 0 {
						v = paths[middle][end]
					}
					if v.Cmp(paths[start][end]) > 0 {
						paths[start][end] = v
					}
				}
			}
		}
	}
	stage := [][]string{}
	for i, c := range cs {
		ok := true
		for j := range cs {
			if paths[i][j].Cmp(paths[j][i]) < 0 {
				ok = false
			}
		}
		if ok {
			stage = append(stage, c)
		}
	}
	single := pairwise(x)
	for _, middle := range x.c {
		for _, start := range x.c {
			for _, end := range x.c {
				if middle != start && middle != end && start != end {
					v := single[start][middle]
					if single[middle][end] < v {
						v = single[middle][end]
					}
					if v > single[start][end] {
						single[start][end] = v
					}
				}
			}
		}
	}
	tied := [][]string{}
	for _, second := range stage {
		disqualified := false
		for _, first := range stage {
			if sameStrings(first, second) {
				continue
			}
			for _, a := range difference(first, second) {
				all := true
				for _, b := range difference(second, first) {
					if single[a][b] <= single[b][a] {
						all = false
					}
				}
				if all {
					disqualified = true
				}
			}
		}
		if !disqualified {
			tied = append(tied, second)
		}
	}
	return result(x, tied[0], len(tied) > 1, trace{{"committees": cs, "links": matrixNumbers(links), "strongestPaths": matrixNumbers(paths), "stageTwoCommittees": stage, "singleWinnerPaths": single, "tiedCommittees": tied}})
}
