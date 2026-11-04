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

def count_quadratic(c, ballots, options):
    # credits records signed voice votes; the budget charges their squares.
    tally = {x: sum(b["credits"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally, "budget": options["budget"]}])

election = {'method': 'quadratic', 'candidates': ['A', 'B', 'C'], 'ballots': [{'credits': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'credits': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'credits': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_quadratic(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
