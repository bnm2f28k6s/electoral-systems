// Batch parity runner. Run from go/: go run ./cmd/parity [-multi].
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"

	"github.com/bnm2f28k6s/electoral-systems/go/internal/jsoninput"
	"github.com/bnm2f28k6s/electoral-systems/go/multi"
	"github.com/bnm2f28k6s/electoral-systems/go/single"
)

func main() {
	committees := flag.Bool("multi", false, "count committees instead of single winners")
	flag.Parse()
	input, err := jsoninput.Decode(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	requests, ok := input.([]any)
	if !ok {
		fmt.Fprintln(os.Stderr, "Expected a JSON array of requests")
		os.Exit(1)
	}
	answers := make([]map[string]any, 0, len(requests))
	for _, request := range requests {
		var result map[string]any
		var err error
		if *committees {
			result, err = multi.Simulate(request)
		} else {
			result, err = single.Simulate(request)
		}
		if err == nil {
			answers = append(answers, map[string]any{"ok": true, "result": result})
			continue
		}
		status := 500
		var singleError *single.ElectionError
		var multiError *multi.ElectionError
		if errors.As(err, &singleError) {
			status = singleError.Status
		} else if errors.As(err, &multiError) {
			status = multiError.Status
		}
		answers = append(answers, map[string]any{"ok": false, "status": status, "error": err.Error()})
	}
	if err := json.NewEncoder(os.Stdout).Encode(answers); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
