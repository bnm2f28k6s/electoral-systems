"""Compile the canonical TypeScript engines into browser ES modules."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPILER = "5.9.3"
SOURCES = ("electoral.ts", "multi_winner.ts", "api.ts", "tsconfig.json", "tsconfig.browser.json")
MODULES = ("electoral.js", "multi_winner.js", "api.js")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_browser(out):
    """Emit directly from source; npm scripts and source maps are disabled."""
    target = Path(out) / "_assets/engine"
    target.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, npm_config_ignore_scripts="true", npm_config_cache=str(ROOT / ".cache/npm"))
    subprocess.run([
        "npx", "--yes", "--package", "typescript@" + COMPILER, "tsc",
        "-p", str(ROOT / "typescript/tsconfig.browser.json"), "--outDir", str(target),
    ], cwd=ROOT, env=env, check=True)
    (target / "package.json").write_text('{"type":"module"}\n')
    manifest = {
        "compiler": "typescript@" + COMPILER,
        "sources": {name: digest(ROOT / "typescript" / name) for name in SOURCES},
        "modules": {name: digest(target / name) for name in MODULES},
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return target


def check_browser(out):
    """Reject stale sources, missing emitted modules, or modified output."""
    target = Path(out) / "_assets/engine"
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["compiler"] == "typescript@" + COMPILER, "Unexpected browser compiler"
    assert manifest["sources"] == {name: digest(ROOT / "typescript" / name) for name in SOURCES}, "Stale browser engine sources"
    assert manifest["modules"] == {name: digest(target / name) for name in MODULES}, "Stale browser engine modules"
    assert json.loads((target / "package.json").read_text()) == {"type": "module"}
    assert not list(target.glob("*.map")), "Browser source maps must not be published"


if __name__ == "__main__":
    compile_browser(ROOT / "site/_build")
