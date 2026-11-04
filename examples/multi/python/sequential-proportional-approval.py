# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def number_map(tally):
    return {x: float(value) if isinstance(value, Fraction) else value for x, value in tally.items()}

def count_sequential_proportional_approval(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        tally = {x: sum((Fraction(b["count"], 1+sum(y in b["approvals"] for y in elected)) for b in ballots if x in b["approvals"]), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'sequential-proportional-approval', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'approvals': ['A', 'B'], 'count': 6}, {'approvals': ['C', 'D'], 'count': 3}, {'approvals': ['D'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_sequential_proportional_approval(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
