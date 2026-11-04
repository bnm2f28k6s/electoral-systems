// Run from go/: go run ./cmd/multi < ../examples/multi/requests/stv.json
package main

import (
	"errors"
	"os"

	"github.com/bnm2f28k6s/electoral-systems/go/internal/command"
	"github.com/bnm2f28k6s/electoral-systems/go/multi"
)

func main() {
	os.Exit(command.Run(os.Stdin, os.Stdout, os.Stderr, multi.Simulate, func(err error) int {
		var electionError *multi.ElectionError
		if errors.As(err, &electionError) {
			return electionError.Status
		}
		return 500
	}))
}
