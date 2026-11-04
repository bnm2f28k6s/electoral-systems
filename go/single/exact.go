package single

import (
	"math/big"
	"sort"
)

func kemenyYoung(ctx *context) map[string]any {
	p := pairwise(ctx)
	high := float64(-1)
	orders := 0
	first := []string{}
	leaders := map[string]bool{}
	var visit func([]string, []string)
	visit = func(prefix, rest []string) {
		if len(rest) == 0 {
			s := float64(0)
			for i, x := range prefix {
				for _, y := range prefix[i+1:] {
					s += p[x][y]
				}
			}
			if s > high {
				high = s
				orders = 0
				first = append([]string{}, prefix...)
				leaders = map[string]bool{}
			}
			if s == high {
				orders++
				leaders[prefix[0]] = true
			}
			return
		}
		for i, x := range rest {
			next := append([]string{}, rest[:i]...)
			next = append(next, rest[i+1:]...)
			visit(append(append([]string{}, prefix...), x), next)
		}
	}
	visit(nil, ctx.candidates)
	w := []string{}
	for _, s := range ctx.candidates {
		if leaders[s] {
			w = append(w, s)
		}
	}
	return answer(ctx, w, trace{{"pairwise": p}, {"bestScore": high, "optimalOrders": orders, "ranking": first}})
}
func reachable(graph map[string][]string, start, target string) bool {
	pending := []string{start}
	seen := map[string]bool{}
	for len(pending) > 0 {
		x := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if x == target {
			return true
		}
		if !seen[x] {
			seen[x] = true
			pending = append(pending, graph[x]...)
		}
	}
	return false
}
func rankedPairs(ctx *context) map[string]any {
	p := pairwise(ctx)
	edges := [][2]string{}
	graph := map[string][]string{}
	for _, x := range ctx.candidates {
		graph[x] = []string{}
		for _, y := range ctx.candidates {
			if p[x][y] > p[y][x] {
				edges = append(edges, [2]string{x, y})
			}
		}
	}
	sort.SliceStable(edges, func(i, j int) bool { return p[edges[i][0]][edges[i][1]] > p[edges[j][0]][edges[j][1]] })
	decisions := []map[string]any{}
	for _, e := range edges {
		locked := !reachable(graph, e[1], e[0])
		if locked {
			graph[e[0]] = append(graph[e[0]], e[1])
		}
		decisions = append(decisions, map[string]any{"from": e[0], "to": e[1], "strength": p[e[0]][e[1]], "locked": locked})
	}
	w := []string{}
	for _, x := range ctx.candidates {
		incoming := false
		for _, y := range ctx.candidates {
			if contains(graph[y], x) {
				incoming = true
			}
		}
		if !incoming {
			w = append(w, x)
		}
	}
	return answer(ctx, w, trace{{"pairwise": p}, {"edges": decisions}})
}
func schulze(ctx *context) map[string]any {
	p := pairwise(ctx)
	paths := map[string]tally{}
	for _, x := range ctx.candidates {
		paths[x] = zeros(ctx.candidates)
		for _, y := range ctx.candidates {
			if x != y && p[x][y] > p[y][x] {
				paths[x][y] = p[x][y]
			}
		}
	}
	for _, middle := range ctx.candidates {
		for _, start := range ctx.candidates {
			for _, end := range ctx.candidates {
				if start != middle && end != middle && start != end {
					paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
				}
			}
		}
	}
	w := []string{}
	for _, x := range ctx.candidates {
		win := true
		for _, y := range ctx.candidates {
			if paths[x][y] < paths[y][x] {
				win = false
			}
		}
		if win {
			w = append(w, x)
		}
	}
	return answer(ctx, w, trace{{"pairwise": p}, {"strongestPaths": paths}})
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

// solveLinear uses exact rationals so feasibility decisions do not depend on tolerances.
func solveLinear(rows [][]int) ([]*big.Rat, bool) {
	n := len(rows)
	a := make([][]*big.Rat, n)
	for i, row := range rows {
		a[i] = make([]*big.Rat, n+1)
		for j := 0; j < n; j++ {
			a[i][j] = new(big.Rat).SetInt64(int64(row[j]))
		}
		a[i][n] = new(big.Rat)
		if i == 0 {
			a[i][n].SetInt64(1)
		}
	}
	for col := 0; col < n; col++ {
		pivot := col
		for pivot < n && a[pivot][col].Sign() == 0 {
			pivot++
		}
		if pivot == n {
			return nil, false
		}
		a[col], a[pivot] = a[pivot], a[col]
		divisor := new(big.Rat).Set(a[col][col])
		for j := 0; j <= n; j++ {
			a[col][j].Quo(a[col][j], divisor)
		}
		for i := 0; i < n; i++ {
			if i != col {
				factor := new(big.Rat).Set(a[i][col])
				for j := 0; j <= n; j++ {
					a[i][j].Sub(a[i][j], new(big.Rat).Mul(factor, a[col][j]))
				}
			}
		}
	}
	out := make([]*big.Rat, n)
	for i := range out {
		out[i] = a[i][n]
	}
	return out, true
}
func maximalLotteries(ctx *context) map[string]any {
	p := pairwise(ctx)
	n := len(ctx.candidates)
	margins := make([][]int, n)
	constraints := make([][]int, 2*n)
	for i, x := range ctx.candidates {
		margins[i] = make([]int, n)
		for j, y := range ctx.candidates {
			margins[i][j] = int(p[x][y] - p[y][x])
		}
	}
	for j := 0; j < n; j++ {
		constraints[j] = make([]int, n)
		constraints[j][j] = 1
		constraints[n+j] = make([]int, n)
		for i := 0; i < n; i++ {
			constraints[n+j][i] = margins[i][j]
		}
	}
	var solution []*big.Rat
	var visit func(int, []int) bool
	visit = func(start int, active []int) bool {
		if len(active) == n-1 {
			ones := make([]int, n)
			for i := range ones {
				ones[i] = 1
			}
			rows := [][]int{ones}
			for _, i := range active {
				rows = append(rows, constraints[i])
			}
			q, ok := solveLinear(rows)
			if !ok {
				return false
			}
			for _, v := range q {
				if v.Sign() < 0 {
					return false
				}
			}
			for j := 0; j < n; j++ {
				sum := new(big.Rat)
				for i := 0; i < n; i++ {
					sum.Add(sum, new(big.Rat).Mul(q[i], new(big.Rat).SetInt64(int64(margins[i][j]))))
				}
				if sum.Sign() < 0 {
					return false
				}
			}
			solution = q
			return true
		}
		for i := start; i <= 2*n-(n-1-len(active)); i++ {
			if visit(i+1, append(append([]int{}, active...), i)) {
				return true
			}
		}
		return false
	}
	if !visit(0, nil) {
		panic("Maximal-lottery feasibility invariant failed")
	}
	prob := make([]float64, n)
	for i, q := range solution {
		prob[i], _ = q.Float64()
	}
	return sample(ctx, prob, trace{{"pairwise": p}, {"margins": margins, "seed": ctx.seed}})
}
