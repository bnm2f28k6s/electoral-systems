# Electoral systems as algorithms

A documentation-first guide to electoral voting systems, their inputs, counting rules, outputs, and tradeoffs. This is an early project, not certified election software.

- [Website](https://bnm2f28k6s.github.io/electoral-systems/)
- [Starting reference: Comparison of electoral systems](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems)
- [Docapella](https://docapella.com/) renders Markdown and OpenAPI 3.0 specifications.

## Current scope

The starter site records the project direction, an algorithm-documentation template, and a deliberately provisional OpenAPI example. No voting algorithm library or API server is implemented yet. Coverage of specific systems, programming languages, tie-breaking policies, and ballot formats remains to be decided.

## Local setup

Prerequisites: Git, Python 3.9+, and Rust/Cargo or Nix. The installer builds a pinned Docapella source revision into ignored `bin/`; it does not install a global tool. `tools/docapella.Cargo.lock` pins the workspace dependency resolution because upstream does not track a lockfile. Native Apple Silicon macOS has been tested. CI builds on Ubuntu using its preinstalled Rust toolchain.

```sh
./scripts/install-docapella.sh
python3 scripts/build.py
python3 scripts/check.py
```

To preview the Pages-compatible production output locally:

```sh
mkdir -p .cache/preview
ln -s ../../site/_build .cache/preview/electoral-systems
python3 -m http.server 8080 --bind 127.0.0.1 --directory .cache/preview
```

Open `http://127.0.0.1:8080/electoral-systems/`. Create the symlink only once. For Docapella's own development server, run `../bin/docapella dev` from `site/`. The upstream server binds all interfaces, so prefer the loopback-only static preview above.

## Publishing

Pushes to `main` build and deploy only `site/_build/` through GitHub Pages Actions. Pull requests build and check without deploying. Workflow actions and Docapella source are commit-pinned. Docapella currently emits root-relative URLs; `scripts/build.py` adapts generated links and search references to `/electoral-systems`, without modifying the generator.

Runtime browser dependencies supplied by Docapella include third-party CDN scripts. The site is not an offline bundle, and those requests have the CDN providers' privacy and availability implications.

## Sources and licensing

The Wikipedia comparison is inspiration and a research entry point, not a copied specification or an authority for every criterion claim. New pages should cite primary definitions where possible. No Wikipedia prose or bundled starter illustrations are redistributed here.

The original project's reuse license is undecided. Public visibility alone is not a blanket reuse grant. Docapella and its dependencies retain their own upstream licenses; the executable and build sources are not committed.
