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

def count_approval(c, ballots, options):
    tally = {x: sum(b["count"] for b in ballots if x in b["approvals"]) for x in c}
    return result(best(tally), [{"tally": tally}])

election = {'method': 'approval', 'candidates': ['A', 'B', 'C'], 'ballots': [{'approvals': ['A', 'B'], 'count': 4}, {'approvals': ['B', 'C'], 'count': 3}, {'approvals': ['C'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_approval(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
