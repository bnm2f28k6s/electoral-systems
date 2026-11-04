// Run from go/: go run ./cmd/electoral < ../examples/requests/borda.json
package main

import (
	"errors"
	"os"

	"github.com/bnm2f28k6s/electoral-systems/go/internal/command"
	"github.com/bnm2f28k6s/electoral-systems/go/single"
)

func main() {
	os.Exit(command.Run(os.Stdin, os.Stdout, os.Stderr, single.Simulate, func(err error) int {
		var electionError *single.ElectionError
		if errors.As(err, &electionError) {
			return electionError.Status
		}
		return 500
	}))
}
