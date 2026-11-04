"""Compare complete multi-winner results in Python and TypeScript.

Agreement is a regression check, not a proof; independent method tests provide
known outcomes and combinatorial oracles. No third-party packages are needed.
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
from multi_winner import ElectionError, METHODS, simulate


def example(method, candidates, seats, rankings, rng, iteration):
    ballots = [{"ranking": ranking, "count": rng.randint(1, 4)} for ranking in rankings]
    if method in {"approval", "proportional-approval", "sequential-proportional-approval", "phragmen"}:
        ballots = [{"approvals": [c for c in candidates if rng.random() < .5], "count": rng.randint(1, 4)} for _ in rankings]
    elif method == "limited-vote":
        limit = max(1, seats - 1)
        ballots = [{"approvals": rng.sample(candidates, rng.randint(0, min(limit, len(candidates)))), "count": rng.randint(1, 4)} for _ in rankings]
    elif method == "reweighted-range":
        ballots = [{"scores": {c: rng.randint(0, 5) for c in candidates}, "count": rng.randint(1, 4)} for _ in rankings]
    elif method == "cumulative":
        ballots = [{"votes": {c: rng.randint(0, 5) for c in candidates}, "count": rng.randint(1, 4)} for _ in rankings]
    elif method == "sortition":
        ballots = []
    elif method == "single-non-transferable" and iteration % 2:
        ballots[0] = {"choice": candidates[-1], "count": 3}
    return {"method": method, "candidates": candidates, "seats": seats, "ballots": ballots,
            "options": {"seed": [0, 1, 4294967295][iteration % 3]}}


def valid_profiles():
    rng = random.Random(94073)
    for iteration in range(60):
        n = rng.randint(1, 6)
        candidates = list("ABCDEF")[:n]
        if iteration % 7 == 0:
            candidates = ["2", "1", "10", "__proto__", "constructor", "toString"][:n]
        if iteration % 11 == 0:
            candidates = ["<A>", "B C", "🌱", "D/E", "quote\"", "F"][:n]
        seats = rng.randint(1, n)
        rankings = [rng.sample(candidates, n) for _ in range(rng.randint(1, 7))]
        for method in METHODS:
            yield example(method, candidates, seats, rankings, rng, iteration)
    for seats in (1, 2, 3):
        candidates = ["A", "B", "C"]
        for method in METHODS:
            yield example(method, candidates, seats, [candidates, candidates[::-1]], rng, 0)
    # Larger non-exhaustive profiles exercise fractional transfers and loads
    # beyond the six-candidate cap used only by committee-comparison methods.
    for n, seats in ((12, 9), (16, 12)):
        candidates = ["C" + str(i) for i in range(n)]
        rankings = [rng.sample(candidates, n) for _ in range(20)]
        for method in METHODS:
            if method not in {"proportional-approval", "minimax-external-opposition", "cpo-stv", "schulze-stv"}:
                yield example(method, candidates, seats, rankings, rng, 0)
    # Exact fractions, zero support, and cutoff ties must agree too.
    for method in ("proportional-approval", "sequential-proportional-approval", "phragmen"):
        for approvals in ([], ["A", "B", "C"]):
            yield {"method": method, "candidates": ["A", "B", "C"], "seats": 2,
                   "ballots": [{"approvals": approvals, "count": 1000000}]}
    for identifier in ("🌱" * 100, "\ufeff"):
        yield {"method": "single-non-transferable", "candidates": [identifier], "seats": 1,
               "ballots": [{"choice": identifier, "count": 1.0}]}


def invalid_profiles():
    valid = {"method": "k-borda", "candidates": ["A", "B", "C"], "seats": 2,
             "ballots": [{"ranking": ["A", "B", "C"]}]}
    yield from [None, [], {}, {**valid, "method": []}, {**valid, "method": "unknown"}]
    for seats in (0, -1, 4, 1.5, True, None, "2"):
        yield {**valid, "seats": seats}
    yield {key: value for key, value in valid.items() if key != "seats"}
    for candidates in ([], ["A", "A"], [" "], ["\u0085"], ["\u001c"], ["🌱" * 101], list(map(str, range(33)))):
        yield {**valid, "candidates": candidates}
    for options in (None, [], {"seed": -1}, {"seed": 4294967296}, {"budget": 0}, {"maxScore": 101}, {"limit": 0}, {"limit": 33}, {"unknown": True}):
        yield {**valid, "options": options}
    for ballot in ({"ranking": ["A", "B"]}, {"ranking": ["A", "A", "C"]}, {"choice": "A"}, {"ranking": ["A", "B", "C"], "count": True}, {"ranking": ["A", "B", "C"], "count": None}, {"ranking": ["A", "B", "C"], "count": 1000001}, {"ranking": ["A", "B", "C"], "approvals": []}):
        yield {**valid, "ballots": [ballot]}
    yield {**valid, "ballots": []}
    yield {**valid, "unknown": True}
    # Allowed field names joined by a delimiter are still unknown field names.
    for key in ("method|candidates", "method|candidates|seats"):
        yield {**valid, key: True}
    for key in ("maxScore|budget", "limit|seed"):
        yield {**valid, "options": {key: 1}}
    for key in ("ranking|approvals", "votes|count"):
        yield {**valid, "ballots": [{"ranking": ["A", "B", "C"], key: True}]}
    yield {**valid, "method": "limited-vote", "ballots": [{"approvals": ["A", "B"]}]}
    yield {**valid, "method": "limited-vote", "ballots": [{"approvals": ["A"]}], "options": {"limit": 2}}
    yield {**valid, "method": "cumulative", "ballots": [{"votes": {"A": 101, "B": 0, "C": 0}}]}
    yield {**valid, "method": "cumulative", "ballots": [{"votes": {"A": -1, "B": 0, "C": 0}}]}
    yield {**valid, "method": "reweighted-range", "ballots": [{"scores": {"A": 6, "B": 0, "C": 0}}]}
    yield {**valid, "method": "sortition"}
    yield {**valid, "ballots": [{"ranking": ["A", "B", "C"], "count": 600000}] * 2}


def same(actual, expected, path="response"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), (path, actual, expected)
        for key in expected:
            same(actual[key], expected[key], path + "." + key)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), (path, actual, expected)
        for index, (a, b) in enumerate(zip(actual, expected)):
            same(a, b, path + "[" + str(index) + "]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)


def main():
    valid, invalid = list(valid_profiles()), list(invalid_profiles())
    requests = valid + invalid
    output = subprocess.run(["node", str(ROOT / "tests/multi_parity_runner.ts")],
                            input=json.dumps(requests), capture_output=True, text=True, check=True, timeout=180)
    actual = json.loads(output.stdout)
    assert len(actual) == len(requests)
    for index, (request, answer) in enumerate(zip(requests, actual)):
        try:
            expected = simulate(copy.deepcopy(request))
        except ElectionError as error:
            assert index >= len(valid), "Generated valid profile was rejected: " + repr(request)
            assert not answer["ok"] and answer["status"] == error.status, (index, request, answer, error.status)
        else:
            assert index < len(valid), "An invalid profile was unexpectedly accepted: " + repr(request)
            assert answer["ok"], (index, request, answer)
            try:
                same(answer["result"], expected)
            except AssertionError as error:
                raise AssertionError((index, request, error.args)) from error
    print(f"PASS: multi-winner full Python/TypeScript parity for {len(valid)} valid profiles across {len(METHODS)} methods; {len(invalid)} invalid profiles agree on status")


if __name__ == "__main__":
    main()
