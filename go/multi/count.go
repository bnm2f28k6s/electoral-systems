package multi

import (
	"math/big"
	"sort"
)

func countApproval(x context) map[string]any {
	t := zeros(x.c)
	for _, b := range x.ballots {
		for _, c := range b.approvals {
			t[c] = add(t[c], rat(b.count))
		}
	}
	return top(x, t, "tally")
}
func countKBorda(x context) map[string]any { return top(x, borda(x), "tally") }
func countBloc(x context) map[string]any {
	t := zeros(x.c)
	for _, b := range x.ballots {
		for _, c := range b.ranking[:x.seats] {
			t[c] = add(t[c], rat(b.count))
		}
	}
	return top(x, t, "tally")
}
func countSingleNonTransferable(x context) map[string]any {
	t := zeros(x.c)
	for _, b := range x.ballots {
		c := b.choice
		if c == "" {
			c = b.ranking[0]
		}
		t[c] = add(t[c], rat(b.count))
	}
	return top(x, t, "tally")
}
func countCumulative(x context) map[string]any {
	t := zeros(x.c)
	for _, b := range x.ballots {
		for _, c := range x.c {
			t[c] = add(t[c], rat(b.values[c]*b.count))
		}
	}
	return top(x, t, "tally")
}
func countMinimax(x context) map[string]any {
	m := pairwise(x)
	t := zeros(x.c)
	for _, c := range x.c {
		v := x.total
		for _, d := range x.c {
			if c != d && m[c][d] < v {
				v = m[c][d]
			}
		}
		t[c] = rat(v)
	}
	r := top(x, t, "simpsonScores")
	r["trace"] = append(trace{{"pairwise": m}}, r["trace"].(trace)...)
	return r
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
func countProportionalApproval(x context) map[string]any {
	cs := combinations(x.c, x.seats)
	scores := []*big.Rat{}
	for _, c := range cs {
		s := rat(0)
		for _, b := range x.ballots {
			n := int64(0)
			for _, a := range c {
				if contains(b.approvals, a) {
					n++
					s = add(s, frac(b.count, n))
				}
			}
		}
		scores = append(scores, s)
	}
	return optimize(x, cs, scores, false, trace{})
}
func sequential(x context, score bool) map[string]any {
	e := []string{}
	tr := trace{}
	tie := false
	for len(e) < x.seats {
		active := difference(x.c, e)
		t := zeros(active)
		ws := []*big.Rat{}
		for _, b := range x.ballots {
			n := int64(0)
			for _, c := range e {
				if score {
					n += b.values[c]
				} else if contains(b.approvals, c) {
					n++
				}
			}
			w := frac(1, 1+n)
			if score {
				w = frac(x.maxScore, x.maxScore+n)
			}
			ws = append(ws, w)
			for _, c := range active {
				v := int64(0)
				if score {
					v = b.values[c]
				} else if contains(b.approvals, c) {
					v = 1
				}
				t[c] = add(t[c], mul(rat(b.count*v), w))
			}
		}
		tied := best(active, t, false)
		row := map[string]any{"round": len(e) + 1, "tally": numeric(t), "selected": tied[0], "tied": tied}
		if score {
			row["weights"] = numbers(ws)
		}
		tr = append(tr, row)
		e = append(e, tied[0])
		tie = tie || len(tied) > 1
	}
	return result(x, e, tie, tr)
}
func countSequentialProportionalApproval(x context) map[string]any { return sequential(x, false) }
func countReweightedRange(x context) map[string]any                { return sequential(x, true) }
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
func countStv(x context) map[string]any {
	q := rat(x.total/int64(x.seats+1) + 1)
	w := weights(x)
	active := append([]string{}, x.c...)
	e := []string{}
	tr := trace{{"quota": number(q)}}
	tie := false
	for len(e) < x.seats {
		if len(active) == x.seats-len(e) {
			e = append(e, active...)
			tr = append(tr, map[string]any{"electedRemaining": append([]string{}, active...)})
			break
		}
		choices, t := choicesTally(x, active, w)
		eligible := []string{}
		for _, c := range active {
			if t[c].Cmp(q) >= 0 {
				eligible = append(eligible, c)
			}
		}
		if len(eligible) > 0 {
			tied := best(eligible, t, false)
			winner := tied[0]
			tie = tie || len(tied) > 1
			f := div(sub(t[winner], q), t[winner])
			transfer(w, choices, winner, f)
			e = append(e, winner)
			active = without(active, winner)
			tr = append(tr, map[string]any{"tally": numeric(t), "elected": winner, "tied": tied, "transferFactor": number(f)})
		} else {
			tied := best(active, t, true)
			loser := tied[len(tied)-1]
			tie = tie || len(tied) > 1
			active = without(active, loser)
			tr = append(tr, map[string]any{"tally": numeric(t), "eliminated": loser, "tied": tied})
		}
	}
	return result(x, e, tie, tr)
}
func draw(c []string, t map[string]*big.Rat, seed uint32) (string, uint32, map[string]any) {
	state := 1664525*seed + 1013904223
	total := rat(0)
	for _, s := range c {
		total = add(total, t[s])
	}
	threshold := frac(int64(state), 4294967296)
	cum := rat(0)
	p := map[string]any{}
	winner := c[len(c)-1]
	chosen := false
	for _, s := range c {
		v := div(t[s], total)
		p[s] = number(v)
		cum = add(cum, v)
		if !chosen && threshold.Cmp(cum) < 0 {
			winner = s
			chosen = true
		}
	}
	return winner, state, p
}
func lottery(x context, randomBallots bool) map[string]any {
	active := append([]string{}, x.c...)
	e := []string{}
	tr := trace{}
	seed := uint32(x.seed)
	for step := 0; step < x.seats; step++ {
		t := zeros(active)
		if randomBallots {
			_, t = choicesTally(x, active, weights(x))
		} else {
			for _, c := range active {
				t[c] = rat(1)
			}
		}
		winner, state, p := draw(active, t, seed)
		seed = state
		e = append(e, winner)
		active = without(active, winner)
		row := map[string]any{"round": step + 1, "probabilities": p, "selected": winner, "state": state}
		if randomBallots {
			row["tally"] = numeric(t)
		}
		tr = append(tr, row)
	}
	return result(x, e, false, tr)
}
func countSortition(x context) map[string]any             { return lottery(x, false) }
func countMultipleRandomBallots(x context) map[string]any { return lottery(x, true) }
func countExpandingApprovals(x context) map[string]any {
	q := droop(x)
	vectors := map[string][]int64{}
	for _, c := range x.c {
		vectors[c] = make([]int64, len(x.c))
	}
	for _, b := range x.ballots {
		for i, c := range b.ranking {
			vectors[c][i] += b.count
		}
	}
	priority := append([]string{}, x.c...)
	sort.SliceStable(priority, func(i, j int) bool {
		for k, a := range vectors[priority[i]] {
			b := vectors[priority[j]][k]
			if a != b {
				return a > b
			}
		}
		return false
	})
	w := weights(x)
	e := []string{}
	depth := 1
	tie := false
	tr := trace{{"quota": number(q), "priority": priority, "rankVectors": vectors}}
	for len(e) < x.seats {
		active := difference(x.c, e)
		t := zeros(active)
		for _, c := range active {
			for i, b := range x.ballots {
				if contains(b.ranking[:depth], c) {
					t[c] = add(t[c], w[i])
				}
			}
		}
		eligible := []string{}
		for _, c := range priority {
			if v, ok := t[c]; ok && v.Cmp(q) >= 0 {
				eligible = append(eligible, c)
			}
		}
		row := map[string]any{"depth": depth, "tally": numeric(t), "eligible": eligible}
		if len(eligible) == 0 {
			tr = append(tr, row)
			depth++
			continue
		}
		winner := eligible[0]
		tied := []string{}
		for _, c := range eligible {
			equal := true
			for i, v := range vectors[c] {
				if v != vectors[winner][i] {
					equal = false
				}
			}
			if equal {
				tied = append(tied, c)
			}
		}
		tie = tie || len(tied) > 1
		e = append(e, winner)
		f := div(sub(t[winner], q), t[winner])
		for i, b := range x.ballots {
			if contains(b.ranking[:depth], winner) {
				w[i] = mul(w[i], f)
			}
		}
		row["selected"] = winner
		row["tied"] = tied
		row["remainingWeights"] = numbers(w)
		tr = append(tr, row)
	}
	return result(x, e, tie, tr)
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
