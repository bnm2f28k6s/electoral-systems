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

def select_top(c, tally, seats):
    ranked = sorted(c, key=lambda x: -tally[x])
    cutoff = tally[ranked[seats-1]]
    tie = any(tally[x] == cutoff for x in ranked[seats:])
    return ordered(c, ranked[:seats]), tie

def tally_result(c, tally, seats, label="tally"):
    winners, tie = select_top(c, tally, seats)
    return {"winners": winners, "tie": tie, "trace": [{label: number_map(tally)}]}

def count_cumulative(c, ballots, seats, options):
    tally = {x: sum(b["votes"][x]*b["count"] for b in ballots) for x in c}
    return tally_result(c, tally, seats)

election = {'method': 'cumulative', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'votes': {'A': 60, 'B': 40, 'C': 0, 'D': 0}, 'count': 6}, {'votes': {'A': 0, 'B': 0, 'C': 60, 'D': 40}, 'count': 3}, {'votes': {'A': 0, 'B': 0, 'C': 0, 'D': 100}, 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_cumulative(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
