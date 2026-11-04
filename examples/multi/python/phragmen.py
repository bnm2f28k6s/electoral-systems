# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def count_phragmen(c, ballots, seats, options):
    loads = [Fraction(0) for b in ballots]
    elected, trace, tie = [], [], False
    for step in range(seats):
        levels = {}
        for x in c:
            if x in elected:
                continue
            support = sum(b["count"] for b in ballots if x in b["approvals"])
            levels[x] = (1+sum((load*b["count"] for b, load in zip(ballots, loads) if x in b["approvals"]), Fraction(0)))/support if support else None
        finite = [v for v in levels.values() if v is not None]
        low = min(finite) if finite else None
        tied = [x for x in c if x in levels and levels[x] == low]
        winner = tied[0]
        elected.append(winner)
        tie |= len(tied) > 1
        if low is not None:
            loads = [low if winner in b["approvals"] else load for b, load in zip(ballots, loads)]
        trace.append({"round": step+1, "loadLevels": {x: float(v) if v is not None else None for x, v in levels.items()}, "selected": winner, "tied": tied, "loads": [float(v) for v in loads]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'phragmen', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'approvals': ['A', 'B'], 'count': 6}, {'approvals': ['C', 'D'], 'count': 3}, {'approvals': ['D'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_phragmen(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
