// Package command implements the shared JSON command-line boundary.
package command

import (
	"encoding/json"
	"io"

	"github.com/bnm2f28k6s/electoral-systems/go/internal/jsoninput"
)

// Simulator counts a request decoded with encoding/json's default number type.
type Simulator func(any) (map[string]any, error)

// Run reads exactly one JSON request. Errors go to stderr, never stdout.
func Run(input io.Reader, output, errors io.Writer, simulate Simulator, status func(error) int) int {
	request, err := jsoninput.Decode(input)
	if err != nil {
		return fail(errors, err, 400)
	}
	result, err := simulate(request)
	if err != nil {
		return fail(errors, err, status(err))
	}
	if err := json.NewEncoder(output).Encode(result); err != nil {
		return fail(errors, err, 500)
	}
	return 0
}

func fail(output io.Writer, err error, status int) int {
	_ = json.NewEncoder(output).Encode(map[string]any{"error": err.Error(), "status": status})
	return 1
}
