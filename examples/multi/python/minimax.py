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

def pairwise(c, ballots):
    matrix = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                matrix[x][y] += b["count"]
    return matrix

def count_minimax(c, ballots, seats, options):
    matrix = pairwise(c, ballots)
    total = sum(b["count"] for b in ballots)
    tally = {x: min([matrix[x][y] for y in c if y != x] or [total]) for x in c}
    counted = tally_result(c, tally, seats, "simpsonScores")
    counted["trace"].insert(0, {"pairwise": matrix})
    return counted

election = {'method': 'minimax', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_minimax(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
