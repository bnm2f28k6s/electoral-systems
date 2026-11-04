# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def best(tally, minimum=False):
    value = (min if minimum else max)(tally.values())
    return [c for c in tally if tally[c] == value]

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_dodgson(c, ballots, options):
    p = pairwise(c, ballots)
    rankings = [b["ranking"] for b in ballots for _ in range(b["count"])]
    threshold = len(rankings)//2 + 1
    tally = {}
    for target in c:
        opponents = [x for x in c if x != target]
        needed = tuple(max(0, threshold-p[target][x]) for x in opponents)
        states = {tuple(0 for _ in opponents): 0}
        for ranking in rankings:
            position = ranking.index(target)
            choices = []
            for swaps in range(position+1):
                passed = set(ranking[position-swaps:position])
                choices.append((swaps, tuple(int(x in passed) for x in opponents)))
            updated = {}
            for gains, cost in states.items():
                for swaps, extra in choices:
                    new = tuple(min(needed[i], gains[i]+extra[i]) for i in range(len(opponents)))
                    updated[new] = min(updated.get(new, float("inf")), cost+swaps)
            states = updated
        tally[target] = states[needed]
    return result(best(tally, True), [{"pairwise": p}, {"adjacentSwaps": tally}])

election = {'method': 'dodgson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 3}, {'ranking': ['B', 'C', 'A'], 'count': 2}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_dodgson(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
