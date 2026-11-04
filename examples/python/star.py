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

def count_star(c, ballots, options):
    tally = {x: sum(b["scores"][x]*b["count"] for b in ballots) for x in c}
    finalists = sorted(c, key=lambda x: -tally[x])[:2]
    trace = [{"stage": "score", "tally": tally, "finalists": finalists}]
    if len(finalists) == 1:
        return result(finalists, trace)
    a, b = finalists
    runoff = {a: sum(v["count"] for v in ballots if v["scores"][a] > v["scores"][b]), b: sum(v["count"] for v in ballots if v["scores"][b] > v["scores"][a])}
    trace.append({"stage": "runoff", "tally": runoff})
    return result([x for x in c if x in best(runoff)], trace)

election = {'method': 'star', 'candidates': ['A', 'B', 'C'], 'ballots': [{'scores': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'scores': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'scores': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_star(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
