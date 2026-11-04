# Go counting engines

Go 1.23+; standard library only. Go 1.27.3 is the primary CI toolchain, with a separate minimum-version compatibility check. There are no runtime Python or Node subprocesses and no downloaded Go dependencies.

## Run a count

From the repository root:

```sh
(cd go && go run ./cmd/electoral < ../examples/requests/borda.json)
(cd go && go run ./cmd/multi < ../examples/multi/requests/stv.json)
go run examples/go/borda.go
go run examples/multi/go/stv.go
```

Both CLIs read exactly one JSON object from stdin and write the result to stdout. On failure they write `{"error":"...","status":400}` to stderr and exit nonzero. Limit violations use status 413. These are CLI error fields, not HTTP responses. The existing HTTP server remains Python-based.

## Use as a library

The module is `github.com/bnm2f28k6s/electoral-systems/go`. Its `single` and `multi` packages export:

- `Simulate(request any) (map[string]any, error)` for dispatch by the request's `method`.
- Method-specific entry points such as `single.CountBorda` and `multi.CountStv`, with the same signature and validation.
- `ElectionError`, whose `Status` and `Message` fields distinguish invalid input from resource limits. Use `errors.As` with `*single.ElectionError` or `*multi.ElectionError`.

Decode requests into `any` with `encoding/json`'s default representation before calling the engine. This uses `map[string]any`, `[]any`, and `float64` JSON numbers, not typed request structs or `json.Number`. Each method-specific entry point expects a request naming that method. The response has the same fields, candidate ordering, traces, tie semantics, seeded draws, and numerical values as the other engines on the retained parity profiles. JSON object key order is not significant.

Candidate order determines priority in intermediate ties. Single-winner final ties remain co-winners; committee results always fill exactly `seats`, with `tie` indicating a selection tie. Exact searches retain the existing small-input limits. Rational rules use exact arithmetic internally before converting display values to JSON numbers. The seeded generator is for reproducible examples, not public election draws.

### JSON Unicode boundary

Go strings represent UTF-8, while Python and JavaScript can retain lone UTF-16 surrogate code units from JSON escapes. The Go CLIs explicitly reject invalid UTF-8 and unpaired surrogate escapes with status 400 instead of allowing `encoding/json` to silently replace them with U+FFFD and change candidate IDs. Ordinary Unicode, astral characters, properly paired surrogate escapes, literal U+FFFD, and literal backslash sequences round-trip unchanged. Python/TypeScript retain their existing lone-surrogate behavior. Library callers own their JSON decoding boundary; use valid Unicode strings rather than relying on replacement decoding.

## Verify and regenerate

From the repository root:

```sh
(cd go && go test -race ./... && go vet ./...)
python3 scripts/check_go_parity.py
python3 -m unittest discover -s tests -p 'test_go_contract.py'
python3 scripts/generate_docs.py
```

The parity script reuses the full single-winner and committee fixture generators, compares complete responses with the existing numerical tolerance, checks invalid-input statuses, and asserts that valid fixtures are actually accepted. Independent algorithm checks remain necessary because agreement alone does not establish correctness.

`cmd/examplegen` uses Go's AST to extract each method's declarations, transitive helper dependencies, receiver methods, and required imports. Generated files in `examples/go/` and `examples/multi/go/` are independent `package main` programs, not copies maintained by hand or wrappers importing the project. Tests run every generated program outside the repository and compare its response with the published fixture. Run individual files with `go run file.go`, not an entire examples directory containing multiple `main` functions.
