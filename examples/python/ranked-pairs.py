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

def count_ranked_pairs(c, ballots, options):
    p = pairwise(c, ballots)
    edges = [(x, y) for x in c for y in c if p[x][y] > p[y][x]]
    # Stable ties: winning votes descending, then candidate input order.
    edges.sort(key=lambda edge: -p[edge[0]][edge[1]])
    graph = {x: [] for x in c}
    decisions = []
    def reachable(start, target):
        pending, seen = [start], set()
        while pending:
            x = pending.pop()
            if x == target:
                return True
            if x not in seen:
                seen.add(x)
                pending.extend(graph[x])
        return False
    for x, y in edges:
        locked = not reachable(y, x)
        if locked:
            graph[x].append(y)
        decisions.append({"from": x, "to": y, "strength": p[x][y], "locked": locked})
    winners = [x for x in c if not any(x in graph[y] for y in c)]
    return result(winners, [{"pairwise": p}, {"edges": decisions}])

election = {'method': 'ranked-pairs', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_ranked_pairs(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
