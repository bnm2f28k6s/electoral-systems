# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def count_sortition(c, ballots, options):
    lottery = [{"candidate": x, "probability": 1/len(c)} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"seed": options["seed"]}], lottery=lottery)

election = {'method': 'sortition', 'candidates': ['A', 'B', 'C'], 'ballots': [], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_sortition(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
