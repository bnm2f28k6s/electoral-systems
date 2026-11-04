package multi

import (
	"encoding/json"
	"math/big"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func decode(t *testing.T, s string) any {
	t.Helper()
	var v any
	if e := json.Unmarshal([]byte(s), &v); e != nil {
		t.Fatal(e)
	}
	return v
}

// The published fixture responses exercise complete traces, not only winners.
func TestPublishedFixtures(t *testing.T) {
	paths, e := filepath.Glob("../../examples/multi/requests/*.json")
	if e != nil {
		t.Fatal(e)
	}
	if len(paths) != 19 {
		t.Fatalf("want 19 fixtures, got %d", len(paths))
	}
	for _, p := range paths {
		t.Run(filepath.Base(p), func(t *testing.T) {
			request, e := os.ReadFile(p)
			if e != nil {
				t.Fatal(e)
			}
			expected, e := os.ReadFile(strings.Replace(p, "/requests/", "/responses/", 1))
			if e != nil {
				t.Fatal(e)
			}
			got, e := Simulate(decode(t, string(request)))
			if e != nil {
				t.Fatal(e)
			}
			encoded, e := json.Marshal(got)
			if e != nil {
				t.Fatal(e)
			}
			if !reflect.DeepEqual(decode(t, string(encoded)), decode(t, string(expected))) {
				t.Fatalf("result differs from fixture:\n%s\nexpected:\n%s", encoded, expected)
			}
		})
	}
}
func TestExactRationals(t *testing.T) {
	a := new(big.Rat).SetFrac(new(big.Int).Add(new(big.Int).Lsh(big.NewInt(1), 100), big.NewInt(1)), new(big.Int).Lsh(big.NewInt(1), 100))
	if number(a) != 1 {
		t.Fatal("expected display rounding")
	}
	tally := map[string]*big.Rat{"A": rat(1), "B": a}
	if got := best([]string{"A", "B"}, tally, false); !reflect.DeepEqual(got, []string{"B"}) {
		t.Fatal(got)
	}
}
func TestValidation(t *testing.T) {
	base := `{"method":"bloc","candidates":["A","B"],"seats":1,"ballots":[{"ranking":["A","B"]}]}`
	tests := []struct {
		name   string
		v      any
		status int
	}{{"null", nil, 400}, {"array", []any{}, 400}, {"missing", map[string]any{}, 400}}
	for _, v := range []string{`"seats":true`, `"seats":1.5`, `"seats":9007199254740992`} {
		tests = append(tests, struct {
			name   string
			v      any
			status int
		}{v, decode(t, strings.Replace(base, `"seats":1`, v, 1)), 400})
	}
	many := decode(t, base).(map[string]any)
	c := []any{}
	for i := 0; i < 33; i++ {
		c = append(c, strings.Repeat("A", i+1))
	}
	many["candidates"] = c
	tests = append(tests, struct {
		name   string
		v      any
		status int
	}{"candidate limit", many, 413})
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, e := Simulate(tt.v)
			ee, ok := e.(*ElectionError)
			if !ok || ee.Status != tt.status {
				t.Fatalf("got %v, want status %d", e, tt.status)
			}
		})
	}
}
func TestUnicodeIdentifiers(t *testing.T) {
	for _, s := range []string{"\u0085", "\u001c", strings.Repeat("🌱", 101)} {
		_, e := Simulate(map[string]any{"method": "sortition", "candidates": []any{s}, "seats": float64(1), "ballots": []any{}})
		if e == nil {
			t.Fatalf("accepted %q", s)
		}
	}
	for _, s := range []string{"\ufeff", strings.Repeat("🌱", 100)} {
		_, e := CountSortition(map[string]any{"method": "sortition", "candidates": []any{s}, "seats": float64(1), "ballots": []any{}})
		if e != nil {
			t.Fatal(e)
		}
	}
}
func TestWrapperChecksMethod(t *testing.T) {
	_, e := CountBloc(decode(t, `{"method":"sortition","candidates":["A"],"seats":1,"ballots":[]}`))
	if e == nil {
		t.Fatal("wrapper accepted another method")
	}
}
func TestGroupKeysAreUnambiguous(t *testing.T) {
	if groupKey([]string{"A B", "C"}) == groupKey([]string{"A", "B C"}) {
		t.Fatal("ambiguous committee group key")
	}
}
