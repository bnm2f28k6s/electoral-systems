"""Verify the Python and TypeScript implementations on reproducible profiles.

Run: python3 scripts/check_parity.py
Requires Node.js 22.18+ for native TypeScript execution, and no npm packages.
This checks complete responses (including traces and lottery probabilities),
plus error statuses for invalid inputs. The method tests supply independently
known winners; agreement alone does not establish algorithmic correctness.
"""
import copy
import json
import math
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from electoral import ElectionError, METHODS, simulate


def valid_profiles():
    rng = random.Random(3823)
    for iteration in range(80):
        n = rng.randint(1, 5)
        candidates = list("ABCDE")[:n]
        if iteration % 10 == 0:
            candidates = ["2", "1", "10", "__proto__", "constructor"][:n]
        if iteration % 13 == 0:
            candidates = ["toString", "A B", "🌱", "x/y", "<C>"][:n]
        rankings = [rng.sample(candidates, n) for _ in range(rng.randint(1, 8))]
        for method in METHODS:
            ballots = [{"ranking": ranking, "count": rng.randint(1, 4)} for ranking in rankings]
            if method == "dodgson":
                ballots = [{"ranking": ranking} for ranking in rankings]
            if method == "approval":
                ballots = [{"approvals": [x for x in candidates if rng.random() < .5], "count": rng.randint(1, 4)} for _ in rankings]
            if method in ("score", "star", "majority-judgment"):
                ballots = [{"scores": {x: rng.randint(0, 5) for x in candidates}, "count": rng.randint(1, 4)} for _ in rankings]
            if method == "quadratic":
                ballots = [{"credits": {x: rng.randint(-3, 3) for x in candidates}, "count": rng.randint(1, 4)} for _ in rankings]
            if method == "sortition":
                ballots = []
            if method in ("plurality", "anti-plurality", "random-ballot") and iteration % 2:
                # Mixed choice and ranking groups also belong to this contract.
                ballots[0] = {"choice": candidates[-1], "count": 3}
            yield {"method": method, "candidates": candidates, "ballots": ballots,
                   "options": {"seed": [0, 1, 4294967295][iteration % 3]}}
    # Compressed histograms expose off-by-one errors in batched median removal.
    for count in (1, 2, 19, 100000):
        yield {"method": "majority-judgment", "candidates": ["2", "1"], "ballots": [
            {"scores": {"2": 5, "1": 4}, "count": count},
            {"scores": {"2": 3, "1": 4}, "count": count},
            {"scores": {"2": 3, "1": 3}, "count": count},
            {"scores": {"2": 0, "1": 0}, "count": count},
        ]}
    # Integral JSON numbers may arrive in exponent or decimal notation.
    yield {"method": "score", "candidates": ["A", "B"],
           "ballots": [{"scores": {"A": 5.0, "B": 2e0}, "count": 2.0}],
           "options": {"maxScore": 5.0, "seed": 1.0, "budget": 100.0}}

    # maxLength counts Unicode characters, including astral symbols, not UTF-16 units.
    for identifier in ("🌱" * 100, "\ufeff"):
        yield {"method": "plurality", "candidates": [identifier],
               "ballots": [{"choice": identifier}]}


def invalid_profiles():
    base = {"method": "borda", "candidates": ["A", "B", "C"],
            "ballots": [{"ranking": ["A", "B", "C"]}]}
    yield None
    yield []
    yield {}
    yield {**base, "method": "unknown"}
    yield {**base, "unknown": True}
    for candidates in ([], [""], [" "], ["A", "A"], ["A" * 101], ["🌱" * 101],
                       ["\u0085"], ["\u001c"], ["\u001d"], ["\u001e"], ["\u001f"],
                       list(map(str, range(33)))):
        yield {**base, "candidates": candidates}
    for options in (None, [], {"seed": -1}, {"seed": 4294967296}, {"seed": 1.5},
                    {"maxScore": 0}, {"maxScore": 101}, {"budget": 0},
                    {"budget": 1000001}, {"seed": True}, {"other": 1}):
        yield {**base, "options": options}
    for ballots in (None, [], [{"ranking": ["A", "B"]}], [{"ranking": ["A", "A", "C"]}],
                    [{"ranking": ["A", "B", "D"]}], [{"choice": "A"}],
                    [{"ranking": ["A", "B", "C"], "choice": "A"}],
                    [{"ranking": ["A", "B", "C"], "count": -1}],
                    [{"ranking": ["A", "B", "C"], "count": True}],
                    [{"ranking": ["A", "B", "C"], "count": None}],
                    [{"ranking": ["A", "B", "C"], "count": 1000000},
                     {"ranking": ["A", "B", "C"]}],
                    [{"ranking": ["A", "B", "C"]}] * 10001):
        yield {**base, "ballots": ballots}
    yield {**base, "method": "approval", "ballots": [{"approvals": ["A", "A"]}]}
    yield {**base, "method": "score", "ballots": [{"scores": {"A": 5, "B": 2}}]}
    yield {**base, "method": "score", "ballots": [{"scores": {"A": 6, "B": 2, "C": 0}}]}
    yield {**base, "method": "score", "ballots": [{"scores": {"A": 5.5, "B": 2, "C": 0}}]}
    yield {**base, "method": "quadratic", "ballots": [{"credits": {"A": 10, "B": 1, "C": 0}}]}
    yield {**base, "method": "sortition"}
    yield {**base, "method": "dodgson", "ballots": [{"ranking": ["A", "B", "C"], "count": 9}]}
    for method, n in (("kemeny-young", 9), ("dodgson", 6), ("maximal-lotteries", 7)):
        candidates = list(map(str, range(n)))
        yield {"method": method, "candidates": candidates, "ballots": [{"ranking": candidates}]}


def equivalent(expected, actual, path="response"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and expected.keys() == actual.keys(), path + " keys"
        for key in expected:
            equivalent(expected[key], actual[key], path + "." + key)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(expected) == len(actual), path + " length"
        for index, (left, right) in enumerate(zip(expected, actual)):
            equivalent(left, right, path + "[" + str(index) + "]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), path + " numeric type"
        assert math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-12), path + " numeric value"
    else:
        assert expected == actual and type(expected) is type(actual), path + " value"


def main():
    valid = list(valid_profiles())
    invalid = list(invalid_profiles())
    requests = valid + invalid
    response = subprocess.run(["node", str(ROOT / "tests/parity_runner.ts")],
                              input=json.dumps(requests), capture_output=True, text=True, check=True)
    actual = json.loads(response.stdout)
    assert len(actual) == len(requests)
    for index, (request, counted) in enumerate(zip(requests, actual)):
        try:
            expected = simulate(copy.deepcopy(request))
        except ElectionError as error:
            assert index >= len(valid), "Generated valid profile was rejected: " + str(request)
            assert counted["ok"] is False and counted["status"] == error.status, str((request, counted, error.status))
        else:
            assert index < len(valid), "An invalid profile was unexpectedly accepted: " + str(request)
            assert counted["ok"] is True, str((request, counted))
            try:
                equivalent(expected, counted["result"])
            except AssertionError as error:
                raise AssertionError(json.dumps({"request": request, "expected": expected, "actual": counted["result"]}, ensure_ascii=False, indent=2)) from error
    print(f"PASS: full Python/TypeScript parity for {len(valid)} valid profiles across {len(METHODS)} methods; {len(invalid)} invalid profiles agree on error status")


if __name__ == "__main__":
    main()
