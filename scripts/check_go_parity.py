"""Compare Go responses and validation statuses against the existing Python engines.

Uses the same reproducible profiles as Python/TypeScript parity, including
candidate-order ties, seeded lotteries, fractional transfers, and exact searches.
Agreement is regression evidence, not a proof of algorithmic correctness.
"""
import copy
import json
from pathlib import Path
import subprocess
import tempfile

import check_parity
import check_multi_parity

ROOT = Path(__file__).resolve().parents[1]


def verify(module, valid, invalid, actual):
    requests = valid + invalid
    assert len(actual) == len(requests), "Go returned the wrong number of answers"
    for index, (request, counted) in enumerate(zip(requests, actual)):
        try:
            expected = module.simulate(copy.deepcopy(request))
        except module.ElectionError as error:
            assert index >= len(valid), "Generated valid profile was rejected: " + repr(request)
            assert counted["ok"] is False and counted["status"] == error.status, (index, request, counted, error.status)
        else:
            assert index < len(valid), "An invalid profile was unexpectedly accepted: " + repr(request)
            assert counted["ok"] is True, (index, request, counted)
            try:
                check_parity.equivalent(expected, counted["result"])
            except AssertionError as error:
                raise AssertionError((index, request, expected, counted)) from error


def main():
    with tempfile.TemporaryDirectory(prefix="electoral-go-parity-") as directory:
        runner = str(Path(directory) / "parity")
        subprocess.run(["go", "build", "-o", runner, "./cmd/parity"], cwd=ROOT / "go", check=True)
        for module, arguments, label in ((check_parity, [], "single-winner"),
                                         (check_multi_parity, ["-multi"], "committee")):
            valid, invalid = list(module.valid_profiles()), list(module.invalid_profiles())
            output = subprocess.run([runner, *arguments], input=json.dumps(valid + invalid),
                                    capture_output=True, text=True, check=True, timeout=180)
            verify(module, valid, invalid, json.loads(output.stdout))
            print(f"PASS: full Python/Go {label} parity for {len(valid)} valid profiles across "
                  f"{len(module.METHODS)} methods; {len(invalid)} invalid profiles agree on status")


if __name__ == "__main__":
    main()
