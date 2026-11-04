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

def first_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        choice = b.get("choice") or next(x for x in b["ranking"] if x in active)
        tally[choice] += b["count"]
    return tally

def count_two_round(c, ballots, options):
    first = first_counts(c, ballots)
    total = sum(first.values())
    trace = [{"round": 1, "tally": first}]
    leaders = best(first)
    if len(c) == 1 or any(first[x]*2 > total for x in c):
        return result(leaders, trace)
    finalists = sorted(c, key=lambda x: -first[x])[:2]
    tally = first_counts(finalists, ballots)
    trace.append({"round": 2, "active": finalists, "tally": tally})
    return result([x for x in c if x in best(tally)], trace)

election = {'method': 'two-round', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_two_round(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
