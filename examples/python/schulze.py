# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_schulze(c, ballots, options):
    p = pairwise(c, ballots)
    paths = {x: {y: p[x][y] if x != y and p[x][y] > p[y][x] else 0 for y in c} for x in c}
    for middle in c:
        for start in c:
            for end in c:
                if len({start, middle, end}) == 3:
                    paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
    winners = [x for x in c if all(paths[x][y] >= paths[y][x] for y in c)]
    return result(winners, [{"pairwise": p}, {"strongestPaths": paths}])

election = {'method': 'schulze', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_schulze(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
