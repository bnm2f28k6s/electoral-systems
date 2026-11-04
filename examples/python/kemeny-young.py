# Python 3.9+. Save as example.py and run: python3 example.py
# Self-contained count for valid input; the API also validates requests.
import itertools
import json
import sys
from fractions import Fraction

def result(winners, trace, **extra):
    return {"winners": winners, "trace": trace, **extra}

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def count_kemeny_young(c, ballots, options):
    p = pairwise(c, ballots)
    high = -1
    winners = set()
    optimal_orders = 0
    first_order = None
    for order in itertools.permutations(c):
        score = sum(p[x][y] for i, x in enumerate(order) for y in order[i+1:])
        if score > high:
            high, winners, optimal_orders, first_order = score, {order[0]}, 1, list(order)
        elif score == high:
            winners.add(order[0])
            optimal_orders += 1
    return result([x for x in c if x in winners], [{"pairwise": p}, {"bestScore": high, "optimalOrders": optimal_orders, "ranking": first_order}])

election = {'method': 'kemeny-young', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_kemeny_young(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
