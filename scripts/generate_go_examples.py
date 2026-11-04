"""Extract standalone Go programs from each engine's declaration dependency graph."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def go_examples(requests, package):
    completed = subprocess.run(
        ["go", "run", "./cmd/examplegen", "-package", package],
        cwd=ROOT / "go", input=json.dumps(requests), text=True,
        capture_output=True, timeout=120,
    )
    if completed.returncode:
        raise RuntimeError("Go example extraction failed: " + completed.stderr)
    examples = json.loads(completed.stdout)
    assert examples.keys() == requests.keys(), "Go example coverage differs from the catalog"
    return examples
