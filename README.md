# Electoral systems as algorithms

A learning resource explaining 25 single-winner methods through plain-language counting rules, worked examples, criteria, Python and TypeScript, and a working local simulation API.

- [Website](https://bnm2f28k6s.github.io/electoral-systems/) (the branch must be merged to `main` before these changes appear there)
- [Method catalog](site/methods.md)
- [Criteria and assumptions](site/criteria.md)
- [Ballot formats and tie policy](site/ballots.md)
- [API guide](site/api-design.md) and [OpenAPI contract](site/openapi.json)
- [Starting comparison](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems)

## Run a count

Python 3.9+ and Node.js 22.18+ are sufficient; neither engine needs third-party runtime packages.

```sh
python3 python/electoral.py < examples/requests/borda.json
node typescript/cli.ts < examples/requests/borda.json
```

Or run the local server:

```sh
python3 python/server.py
```

In another terminal:

```sh
curl http://127.0.0.1:8000/systems
curl --fail-with-body http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @examples/requests/instant-runoff.json
```

The server executes the Python engine; it is not a mock response service. GitHub Pages serves only static documentation. Each file in `examples/python/` and `examples/typescript/` is also independently runnable without project imports, and includes its own sample input. The examples focus on valid data; the complete engines perform input validation.

## Coverage

Every method row from the reference's single-winner table has a chapter, matching Python and TypeScript implementation, API request and executed response, and all 25 criterion entries. The criteria distinguish pass, fail, conditional, unverified, and not applicable. Qualifications matter: a ranked criterion need not mean the same thing for scores, and a lottery's properties concern its distribution rather than one seeded draw.

Variants are explicit: complete strict rankings, input-order priority for intermediate ties, final co-winners, margin Minimax, winning-votes Ranked Pairs and Schulze, lower-median majority judgment, and fixed-preference two-round simulation. Quadratic voting is an equal-budget signed voice-vote demonstration. Random ballot, sortition, and maximal lotteries return both a lottery and reproducible draw. Exhaustive algorithms have small documented limits.

The code does not implement voter eligibility, secrecy, election administration, or certification. It is intended for synthetic teaching profiles. Go, Rust, and further languages can be added later; Python and TypeScript cover every method now.

## Verify code and examples

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_typescript.ts
python3 scripts/check_parity.py
```

Tests execute all 50 standalone programs and every documented HTTP request. Independent checks include Condorcet profiles, Smith sets against exhaustive subsets, Dodgson against unrestricted adjacent-swap search, majority judgment against naive median deletion, and lottery feasibility. The retained parity check compares complete Python and TypeScript results over 2,007 profiles and checks 50 invalid inputs.

For optional static TypeScript checking with the pinned compiler:

```sh
npm_config_cache="$PWD/.cache/npm" npm_config_ignore_scripts=true \
  npx --yes --package typescript@5.9.3 tsc -p typescript/tsconfig.json
```

## Build the documentation

Prerequisites: Git, Python 3.9+, and Rust/Cargo or Nix. The installer builds a pinned Docapella revision into ignored `bin/`. `tools/docapella.Cargo.lock` pins its dependency resolution. Native Apple Silicon macOS and Ubuntu are supported by the existing build workflow.

```sh
./scripts/install-docapella.sh
python3 scripts/generate_docs.py
python3 scripts/generate_openapi.py
python3 scripts/build.py
python3 scripts/check.py
```

Edit `data/methods.json`, `data/criteria.json`, the engines, or `scripts/fixtures.py` to update generated chapters and examples. Run both generators after a change and commit the generated files too. The generators extract each method's helper dependencies directly from the engines; they do not maintain separate algorithm copies by hand. Review [`site/algorithm-template.md`](site/algorithm-template.md) for chapter conventions. Components use [Docapella's documented syntax](https://docapella.com/components), including language selectors and steps.

To preview the Pages-compatible production output locally:

```sh
mkdir -p .cache/preview
ln -s ../../site/_build .cache/preview/electoral-systems
python3 -m http.server 8080 --bind 127.0.0.1 --directory .cache/preview
```

Open `http://127.0.0.1:8080/electoral-systems/`. Create the symlink only once. Docapella's own development server is available with `../bin/docapella dev` from `site/`; it binds all interfaces, so the loopback static preview is the default here.

## Publishing

Pushes to `main` build and deploy `site/_build/` through GitHub Pages Actions. Pushes to `codex/initial-single-winner-examples` and pull requests run checks without deployment. Workflow actions and Docapella source are commit-pinned. `scripts/build.py` adapts generated links and search references to `/electoral-systems`, without modifying the generator or site styling.

Docapella supplies third-party CDN browser dependencies; the documentation is not an offline bundle.

## Sources and licensing

The comparison is a coverage roadmap, not a copied specification or the authority for every criterion claim. [Sources and interpretation notes](site/sources.md) link method definitions, research papers, and primary implementation documentation. Criterion notes identify uncertainty rather than filling gaps with invented guarantees.

The original project's reuse license is undecided. Public visibility alone is not a blanket reuse grant. Docapella and its dependencies retain their upstream licenses; the executable and build sources are not committed.
