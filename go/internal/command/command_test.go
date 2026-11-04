package command

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"strings"
	"testing"
)

func TestRun(t *testing.T) {
	for _, test := range []struct {
		name, input          string
		engineError          error
		wantCode, wantStatus int
	}{
		{"valid", `{"method":"approval"}`, nil, 0, 0},
		{"empty", "", nil, 1, 400},
		{"invalid JSON", "{", nil, 1, 400},
		{"trailing JSON", "{} {}", nil, 1, 400},
		{"trailing junk", "{} x", nil, 1, 400},
		{"limit", "{}", errors.New("Too many candidates"), 1, 413},
	} {
		t.Run(test.name, func(t *testing.T) {
			var output, stderr bytes.Buffer
			calls := 0
			code := Run(strings.NewReader(test.input), &output, &stderr, func(request any) (map[string]any, error) {
				calls++
				return map[string]any{"winners": []string{"🌱"}}, test.engineError
			}, func(err error) int { return 413 })
			if code != test.wantCode {
				t.Fatalf("exit code %d, want %d", code, test.wantCode)
			}
			if code == 0 {
				if calls != 1 || stderr.Len() != 0 || !strings.Contains(output.String(), "🌱") {
					t.Fatal("incorrect success output")
				}
			} else {
				if output.Len() != 0 {
					t.Fatal("error wrote to stdout")
				}
				var answer struct {
					Status int
					Error  string
				}
				if err := json.Unmarshal(stderr.Bytes(), &answer); err != nil {
					t.Fatal(err)
				}
				if answer.Status != test.wantStatus || answer.Error == "" {
					t.Fatalf("bad error: %+v", answer)
				}
				if test.engineError == nil && calls != 0 {
					t.Fatal("invalid JSON reached counting engine")
				}
			}
		})
	}
}

func TestWriteFailureIsReported(t *testing.T) {
	var stderr bytes.Buffer
	if code := Run(strings.NewReader("{}"), failingWriter{}, &stderr, func(any) (map[string]any, error) {
		return map[string]any{}, nil
	}, func(error) int { return 500 }); code != 1 || !strings.Contains(stderr.String(), `"status":500`) {
		t.Fatal("output error was not reported")
	}
}

type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, io.ErrClosedPipe }
