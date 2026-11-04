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

def count_bucklin(c, ballots, options):
    tally = dict.fromkeys(c, 0)
    total = sum(b["count"] for b in ballots)
    trace = []
    for depth in range(len(c)):
        for b in ballots:
            tally[b["ranking"][depth]] += b["count"]
        trace.append({"depth": depth+1, "tally": tally.copy()})
        if max(tally.values())*2 > total:
            return result(best(tally), trace)
    return result(best(tally), trace)

election = {'method': 'bucklin', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_bucklin(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
