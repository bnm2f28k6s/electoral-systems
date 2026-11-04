package jsoninput

import (
	"strings"
	"testing"
)

func TestUnicodeBoundary(t *testing.T) {
	for _, test := range []struct {
		source   string
		valid    bool
		expected string
	}{
		{`"🌱"`, true, "🌱"},
		{`"\ud83c\udf31"`, true, "🌱"},
		{`"\ufffd"`, true, "�"},
		{`"\\ud800"`, true, `\ud800`},
		{`"\ud800"`, false, ""},
		{`"\udfff"`, false, ""},
		{`"A\ud800B"`, false, ""},
		{`"\ud800\ud800"`, false, ""},
		{`"\ud800\u0041"`, false, ""},
		{`"\ud800\u"`, false, ""},
		{`"\ud83c\udf31\ud800"`, false, ""},
		{`{"\ud800": 1}`, false, ""},
		{"\"\xff\"", false, ""},
		{`{} {}`, false, ""},
	} {
		t.Run(test.source, func(t *testing.T) {
			result, err := Decode(strings.NewReader(test.source))
			if (err == nil) != test.valid {
				t.Fatalf("valid=%v, error=%v", test.valid, err)
			}
			if test.valid && result != test.expected {
				t.Fatalf("got %q, want %q", result, test.expected)
			}
		})
	}
}
