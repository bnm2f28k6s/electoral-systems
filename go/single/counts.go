package single

import "sort"

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
func condorcet(c []string, p map[string]tally) []string {
	out := []string{}
	for _, x := range c {
		win := true
		for _, y := range c {
			if x != y && p[x][y] <= p[y][x] {
				win = false
			}
		}
		if win {
			out = append(out, x)
		}
	}
	return out
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
func plurality(ctx *context) map[string]any {
	t := firstCounts(ctx, ctx.candidates)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t}})
}
func antiPlurality(ctx *context) map[string]any {
	t := zeros(ctx.candidates)
	for _, b := range ctx.ballots {
		s := b.choice
		if !b.hasChoice {
			s = b.ranking[len(b.ranking)-1]
		}
		t[s] += float64(b.count)
	}
	return answer(ctx, best(ctx.candidates, t, true), trace{{"vetoes": t}})
}
func finalists(c []string, t tally) []string {
	out := append([]string{}, c...)
	sort.SliceStable(out, func(i, j int) bool { return t[out[i]] > t[out[j]] })
	return out[:min(2, len(out))]
}
func twoRound(ctx *context) map[string]any {
	t := firstCounts(ctx, ctx.candidates)
	tr := trace{{"round": 1, "tally": t}}
	w := best(ctx.candidates, t, false)
	if len(ctx.candidates) == 1 || t[w[0]]*2 > float64(ctx.total) {
		return answer(ctx, w, tr)
	}
	f := finalists(ctx.candidates, t)
	t = firstCounts(ctx, f)
	tr = append(tr, map[string]any{"round": 2, "active": f, "tally": t})
	return answer(ctx, best(f, t, false), tr)
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
func instantRunoff(ctx *context) map[string]any      { return elimination(ctx, "instant-runoff") }
func coombs(ctx *context) map[string]any             { return elimination(ctx, "coombs") }
func nanson(ctx *context) map[string]any             { return elimination(ctx, "nanson") }
func baldwin(ctx *context) map[string]any            { return elimination(ctx, "baldwin") }
func tidemanAlternative(ctx *context) map[string]any { return elimination(ctx, "tideman-alternative") }
func borda(ctx *context) map[string]any {
	t := bordaCounts(ctx, ctx.candidates)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t}})
}
func minimax(ctx *context) map[string]any {
	p := pairwise(ctx)
	t := zeros(ctx.candidates)
	for _, x := range ctx.candidates {
		for _, y := range ctx.candidates {
			t[x] = max(t[x], p[y][x]-p[x][y])
		}
	}
	return answer(ctx, best(ctx.candidates, t, true), trace{{"pairwise": p}, {"worstDefeat": t}})
}
func copeland(ctx *context) map[string]any {
	p := pairwise(ctx)
	t := zeros(ctx.candidates)
	for _, x := range ctx.candidates {
		for _, y := range ctx.candidates {
			if x != y {
				if p[x][y] > p[y][x] {
					t[x]++
				} else if p[x][y] == p[y][x] {
					t[x] += .5
				}
			}
		}
	}
	return answer(ctx, best(ctx.candidates, t, false), trace{{"pairwise": p}, {"tally": t}})
}
func black(ctx *context) map[string]any {
	p := pairwise(ctx)
	w := condorcet(ctx.candidates, p)
	if len(w) > 0 {
		return answer(ctx, w, trace{{"pairwise": p}, {"condorcet": w}})
	}
	t := bordaCounts(ctx, ctx.candidates)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"pairwise": p}, {"fallback": "borda"}, {"tally": t}})
}
func bucklin(ctx *context) map[string]any {
	t := zeros(ctx.candidates)
	tr := trace{}
	for depth := range ctx.candidates {
		for _, b := range ctx.ballots {
			t[b.ranking[depth]] += float64(b.count)
		}
		snapshot := zeros(ctx.candidates)
		for k, v := range t {
			snapshot[k] = v
		}
		tr = append(tr, map[string]any{"depth": depth + 1, "tally": snapshot})
		if t[best(ctx.candidates, t, false)[0]]*2 > float64(ctx.total) {
			break
		}
	}
	return answer(ctx, best(ctx.candidates, t, false), tr)
}
func approval(ctx *context) map[string]any {
	t := zeros(ctx.candidates)
	for _, b := range ctx.ballots {
		for _, s := range b.approvals {
			t[s] += float64(b.count)
		}
	}
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t}})
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
func score(ctx *context) map[string]any {
	t := scoreCounts(ctx)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t}})
}
func quadratic(ctx *context) map[string]any {
	t := scoreCounts(ctx)
	return answer(ctx, best(ctx.candidates, t, false), trace{{"tally": t, "budget": ctx.budget}})
}
func star(ctx *context) map[string]any {
	t := scoreCounts(ctx)
	f := finalists(ctx.candidates, t)
	tr := trace{{"stage": "score", "tally": t, "finalists": f}}
	if len(f) == 1 {
		return answer(ctx, f, tr)
	}
	runoff := zeros(f)
	for _, b := range ctx.ballots {
		if b.values[f[0]] > b.values[f[1]] {
			runoff[f[0]] += float64(b.count)
		}
		if b.values[f[1]] > b.values[f[0]] {
			runoff[f[1]] += float64(b.count)
		}
	}
	return answer(ctx, best(f, runoff, false), append(tr, map[string]any{"stage": "runoff", "tally": runoff}))
}
func median(h []int) int {
	n := 0
	for _, v := range h {
		n += v
	}
	if n == 0 {
		return -1
	}
	position := (n - 1) / 2
	sum := 0
	for grade, v := range h {
		sum += v
		if sum > position {
			return grade
		}
	}
	return -1
}
func majorityJudgment(ctx *context) map[string]any {
	h := map[string][]int{}
	initial := zeros(ctx.candidates)
	snap := map[string][]int{}
	for _, s := range ctx.candidates {
		h[s] = make([]int, ctx.maxScore+1)
		for _, b := range ctx.ballots {
			h[s][b.values[s]] += b.count
		}
		initial[s] = float64(median(h[s]))
		snap[s] = append([]int{}, h[s]...)
	}
	tr := trace{{"majorityGrades": initial, "histograms": snap}}
	active := best(ctx.candidates, initial, false)
	removed := 0
	for len(active) > 1 && median(h[active[0]]) >= 0 {
		same := true
		for _, s := range active {
			for i, v := range h[s] {
				if v != h[active[0]][i] {
					same = false
				}
			}
		}
		if same {
			break
		}
		batch := ctx.total
		for _, s := range active {
			grade := median(h[s])
			n, below := 0, 0
			for i, v := range h[s] {
				n += v
				if i < grade {
					below += v
				}
			}
			batch = min(batch, min(n-1-2*below, 2*below+2*h[s][grade]-n)+1)
		}
		grades := zeros(active)
		for _, s := range active {
			h[s][median(h[s])] -= batch
			grades[s] = float64(median(h[s]))
		}
		removed += batch
		active = best(active, grades, false)
	}
	return answer(ctx, active, append(tr, map[string]any{"medianGradesRemoved": removed, "remaining": active}))
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
func randomBallot(ctx *context) map[string]any {
	t := firstCounts(ctx, ctx.candidates)
	p := make([]float64, len(ctx.candidates))
	for i, s := range ctx.candidates {
		p[i] = t[s] / float64(ctx.total)
	}
	return sample(ctx, p, trace{{"tally": t, "seed": ctx.seed}})
}
func sortition(ctx *context) map[string]any {
	p := make([]float64, len(ctx.candidates))
	for i := range p {
		p[i] = 1 / float64(len(p))
	}
	return sample(ctx, p, trace{{"seed": ctx.seed}})
}
