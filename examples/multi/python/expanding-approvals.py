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

def droop_fraction(total, seats):
    return Fraction(total, seats+1) + Fraction(1, (seats+1)**2)

def count_expanding_approvals(c, ballots, seats, options):
    quota = droop_fraction(sum(b["count"] for b in ballots), seats)
    rank_vectors = {x: tuple(sum(b["count"] for b in ballots if b["ranking"][depth] == x) for depth in range(len(c))) for x in c}
    priority = sorted(c, key=lambda x: tuple(-n for n in rank_vectors[x]))
    weights = [Fraction(b["count"]) for b in ballots]
    elected, depth, tie = [], 1, False
    trace = [{"quota": float(quota), "priority": priority, "rankVectors": {x: list(v) for x, v in rank_vectors.items()}}]
    while len(elected) < seats:
        tally = {x: sum((w for b, w in zip(ballots, weights) if x in b["ranking"][:depth]), Fraction(0)) for x in c if x not in elected}
        eligible = [x for x in priority if x in tally and tally[x] >= quota]
        if not eligible:
            trace.append({"depth": depth, "tally": number_map(tally), "eligible": []})
            depth += 1
            continue
        winner = eligible[0]
        tied = [x for x in eligible if rank_vectors[x] == rank_vectors[winner]]
        tie |= len(tied) > 1
        elected.append(winner)
        factor = (tally[winner]-quota)/tally[winner]
        weights = [w*factor if winner in b["ranking"][:depth] else w for b, w in zip(ballots, weights)]
        trace.append({"depth": depth, "tally": number_map(tally), "eligible": eligible, "selected": winner, "tied": tied, "remainingWeights": [float(w) for w in weights]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'expanding-approvals', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_expanding_approvals(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
