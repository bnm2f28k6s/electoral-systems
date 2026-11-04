# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def first_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        choice = b.get("choice") or next(x for x in b["ranking"] if x in active)
        tally[choice] += b["count"]
    return tally

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def count_random_ballot(c, ballots, options):
    tally = first_counts(c, ballots)
    total = sum(tally.values())
    lottery = [{"candidate": x, "probability": tally[x]/total} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"tally": tally, "seed": options["seed"]}], lottery=lottery)

election = {'method': 'random-ballot', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_random_ballot(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
