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

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        ranking = [x for x in b["ranking"] if x in active]
        for position, x in enumerate(ranking):
            tally[x] += (len(c) - position - 1) * b["count"]
    return tally

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def condorcet(c, p):
    return [x for x in c if all(x == y or p[x][y] > p[y][x] for y in c)]

def count_borda(c, ballots, options):
    tally = borda_counts(c, ballots)
    return result(best(tally), [{"tally": tally}])

def count_black(c, ballots, options):
    p = pairwise(c, ballots)
    winners = condorcet(c, p)
    if winners:
        return result(winners, [{"pairwise": p}, {"condorcet": winners}])
    fallback = count_borda(c, ballots, options)
    return result(fallback["winners"], [{"pairwise": p}, {"fallback": "borda"}] + fallback["trace"])

election = {'method': 'black', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_black(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
