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

def count_reweighted_range(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        weights = [Fraction(options["maxScore"], options["maxScore"]+sum(b["scores"][x] for x in elected)) for b in ballots]
        tally = {x: sum((b["count"]*weight*b["scores"][x] for b, weight in zip(ballots, weights)), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "weights": [float(w) for w in weights], "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'reweighted-range', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'scores': {'A': 5, 'B': 4, 'C': 0, 'D': 0}, 'count': 6}, {'scores': {'A': 0, 'B': 0, 'C': 5, 'D': 4}, 'count': 3}, {'scores': {'A': 0, 'B': 0, 'C': 4, 'D': 5}, 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_reweighted_range(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
