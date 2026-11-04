package single

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func decoded(t *testing.T, s string) any {
	t.Helper()
	var r any
	if err := json.Unmarshal([]byte(s), &r); err != nil {
		t.Fatal(err)
	}
	return r
}
func TestPublishedExamples(t *testing.T) {
	paths, err := filepath.Glob("../../examples/requests/*.json")
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 25 {
		t.Fatalf("want 25 examples, got %d", len(paths))
	}
	for _, p := range paths {
		t.Run(filepath.Base(p), func(t *testing.T) {
			b, err := os.ReadFile(p)
			if err != nil {
				t.Fatal(err)
			}
			out, err := Simulate(decoded(t, string(b)))
			if err != nil {
				t.Fatal(err)
			}
			want, err := os.ReadFile(filepath.Join("../../examples/responses", filepath.Base(p)))
			if err != nil {
				t.Fatal(err)
			}
			encoded, err := json.Marshal(out)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(decoded(t, string(encoded)), decoded(t, string(want))) {
				t.Fatalf("got %s; want %s", encoded, want)
			}
		})
	}
}
func TestValidation(t *testing.T) {
	for _, tc := range []struct {
		request string
		status  int
	}{
		{`null`, 400},
		{`{"method":"Plurality","candidates":["A"],"ballots":[{"choice":"A"}]}`, 400},
		{`{"method":"quadratic","candidates":["A"],"ballots":[{"credits":{"A":9007199254740991}}]}`, 400},
		{`{"method":"quadratic","candidates":["A"],"ballots":[{"credits":{"A":-9007199254740991}}]}`, 400},
		{`{"method":"score","candidates":["A"],"ballots":[{"scores":{"A":9007199254740992}}]}`, 400},
		{`{"method":"borda","candidates":["A"],"ballots":[{"ranking":["A"],"count":1000000},{"ranking":["A"]}]}`, 413},
		{`{"method":"dodgson","candidates":["A"],"ballots":[{"ranking":["A"],"count":9}]}`, 413},
		{`{"method":"plurality","candidates":["\u001c"],"ballots":[{"choice":"\u001c"}]}`, 400},
	} {
		_, err := Simulate(decoded(t, tc.request))
		var election *ElectionError
		if !errors.As(err, &election) || election.Status != tc.status {
			t.Fatalf("%s: got %v, want status %d", tc.request, err, tc.status)
		}
	}
}
func TestUnicodeAndArrayTypes(t *testing.T) {
	s := strings.Repeat("🌱", 100)
	r := map[string]any{"method": "plurality", "candidates": []any{s}, "ballots": []any{map[string]any{"choice": s}}}
	if _, err := CountPlurality(r); err != nil {
		t.Fatal(err)
	}
	r["candidates"] = []string{s}
	if _, err := Simulate(r); err == nil {
		t.Fatal("typed []string must not masquerade as decoded JSON array")
	}
}
func TestQuadraticBudgetBoundary(t *testing.T) {
	for _, value := range []string{"1000", "-1000"} {
		r := decoded(t, `{"method":"quadratic","candidates":["A"],"ballots":[{"credits":{"A":`+value+`},"count":1000000}],"options":{"budget":1000000}}`)
		out, err := CountQuadratic(r)
		if err != nil {
			t.Fatal(err)
		}
		if out["tie"] != false {
			t.Fatal(out)
		}
	}
}
func TestMethodWrapperRejectsWrongMethod(t *testing.T) {
	_, err := CountBorda(decoded(t, `{"method":"plurality","candidates":["A"],"ballots":[{"choice":"A"}]}`))
	if err == nil {
		t.Fatal("method-specific entry point accepted another method")
	}
}
func TestMedianEmpty(t *testing.T) {
	if median([]int{0, 0}) != -1 {
		t.Fatal("empty median")
	}
}

func TestArchitectureIndependentIntegers(t *testing.T) {
	for _, value := range []int64{4294967295, 9007199254740991, -9007199254740991} {
		got, ok := number(float64(value))
		if !ok || got != value {
			t.Fatalf("integer conversion changed %d to %d, valid=%v", value, got, ok)
		}
	}
	out, err := CountSortition(decoded(t, `{"method":"sortition","candidates":["A"],"ballots":[],"options":{"seed":4294967295}}`))
	if err != nil {
		t.Fatal(err)
	}
	if out["trace"].(trace)[0]["seed"] != uint32(4294967295) {
		t.Fatal("uint32 seed changed during validation")
	}
}
