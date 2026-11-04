#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REV=789583bb81bbae43a8600b0b4f525a9bce387038
mkdir -p "${TMPDIR:-$ROOT/.cache}"
WORK=$(mktemp -d "${TMPDIR:-$ROOT/.cache}/electoral-docapella.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
# The upstream workspace does not track Cargo.lock. Keep our reviewed resolution.
git clone --quiet https://github.com/Doctave/docapella.git "$WORK/source"
git -C "$WORK/source" checkout --quiet --detach "$REV"
test "$(git -C "$WORK/source" rev-parse HEAD)" = "$REV"
cp "$ROOT/tools/docapella.Cargo.lock" "$WORK/source/Cargo.lock"
build() {
  cargo build --release --locked --manifest-path "$WORK/source/Cargo.toml" -p docapella
}
if command -v cargo >/dev/null 2>&1; then
  build
elif command -v nix >/dev/null 2>&1; then
  nix shell github:NixOS/nixpkgs/31ecbaca1bdefa45dffc409f0250bd8039ea0010#cargo github:NixOS/nixpkgs/31ecbaca1bdefa45dffc409f0250bd8039ea0010#rustc --command cargo build --release --locked --manifest-path "$WORK/source/Cargo.toml" -p docapella
else
  printf '%s\n' 'Install Rust/Cargo or Nix before running this installer.' >&2
  exit 1
fi
mkdir -p "$ROOT/bin"
cp "${CARGO_TARGET_DIR:-$WORK/source/target}/release/docapella" "$ROOT/bin/docapella"
"$ROOT/bin/docapella" --version
