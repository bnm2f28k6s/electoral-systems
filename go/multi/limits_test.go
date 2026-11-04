package multi

import (
	"fmt"
	"math"
	"testing"
)

func TestThirtyTwoCandidatesAndLargeCounts(t *testing.T) {
	candidates := make([]any, 32)
	ranking := make([]any, 32)
	values := map[string]any{}
	for i := range candidates {
		s := fmt.Sprintf("C%d", i)
		candidates[i] = s
		ranking[i] = s
		values[s] = float64(31250)
	}
	r := map[string]any{"method": "cumulative", "candidates": candidates, "seats": float64(32), "options": map[string]any{"budget": float64(1000000)}, "ballots": []any{map[string]any{"votes": values, "count": float64(1000000)}}}
	got, e := CountCumulative(r)
	if e != nil {
		t.Fatal(e)
	}
	if len(got["winners"].([]string)) != 32 {
		t.Fatal(got)
	}
	tally := got["trace"].(trace)[0]["tally"].(map[string]any)
	if tally["C0"] != float64(31250000000) {
		t.Fatal(tally)
	}
	r["method"] = "k-borda"
	r["ballots"] = []any{map[string]any{"ranking": ranking, "count": float64(1000000)}}
	got, e = CountKBorda(r)
	if e != nil {
		t.Fatal(e)
	}
	tally = got["trace"].(trace)[0]["tally"].(map[string]any)
	if tally["C0"] != float64(31000000) {
		t.Fatal(tally)
	}
	r["method"] = "sortition"
	r["ballots"] = []any{}
	r["options"] = map[string]any{"seed": float64(4294967295)}
	got, e = CountSortition(r)
	if e != nil {
		t.Fatal(e)
	}
	if len(got["winners"].([]string)) != 32 {
		t.Fatal(got)
	}
}
func TestExtremeNumbersAndLimits(t *testing.T) {
	base := func() map[string]any {
		return map[string]any{"method": "cumulative", "candidates": []any{"A"}, "seats": float64(1), "ballots": []any{map[string]any{"votes": map[string]any{"A": float64(1)}}}}
	}
	for _, v := range []float64{math.NaN(), math.Inf(1), math.Inf(-1), 9007199254740992, -9007199254740992, math.MaxFloat64} {
		for _, field := range []string{"seats", "count", "votes", "seed"} {
			r := base()
			switch field {
			case "seats":
				r[field] = v
			case "seed":
				r["options"] = map[string]any{"seed": v}
			case "count":
				r["ballots"].([]any)[0].(map[string]any)[field] = v
			case "votes":
				r["ballots"].([]any)[0].(map[string]any)[field] = map[string]any{"A": v}
			}
			if _, e := Simulate(r); e == nil {
				t.Fatalf("accepted %s=%v", field, v)
			}
		}
	}
	r := base()
	r["ballots"] = []any{map[string]any{"votes": map[string]any{"A": float64(0)}, "count": float64(600000)}, map[string]any{"votes": map[string]any{"A": float64(0)}, "count": float64(600000)}}
	if _, e := Simulate(r); e == nil || e.(*ElectionError).Status != 413 {
		t.Fatalf("represented voter cap: %v", e)
	}
	r = base()
	ballots := make([]any, 10001)
	for i := range ballots {
		ballots[i] = map[string]any{"votes": map[string]any{"A": float64(0)}}
	}
	r["ballots"] = ballots
	if _, e := Simulate(r); e == nil || e.(*ElectionError).Status != 413 {
		t.Fatalf("ballot group cap: %v", e)
	}
}
