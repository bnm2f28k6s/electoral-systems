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

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    active = set(c)
    for b in ballots:
        ranking = [x for x in b["ranking"] if x in active]
        for position, x in enumerate(ranking):
            tally[x] += (len(c) - position - 1) * b["count"]
    return tally

def pairwise(c, ballots):
    p = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                p[x][y] += b["count"]
    return p

def smith_set(c, p):
    # Closure adds every outsider not strictly beaten by each current member.
    closures = []
    for start in c:
        group = {start}
        while True:
            expanded = group | {y for y in c if any(p[x][y] <= p[y][x] for x in group if x != y)}
            if expanded == group:
                break
            group = expanded
        closures.append(group)
    smallest = min(closures, key=len)
    return [x for x in c if x in smallest]

def elimination(c, ballots, mode):
    active = c[:]
    trace = []
    total = sum(b["count"] for b in ballots)
    p = pairwise(c, ballots) if mode == "tideman-alternative" else None
    while len(active) > 1:
        if p is not None:
            smith = smith_set(active, p)
            if smith != active:
                trace.append({"active": active[:], "smith": smith})
                active = smith
                if len(active) == 1:
                    break
        first = first_counts(active, ballots)
        if mode in {"instant-runoff", "coombs", "tideman-alternative"}:
            majority = [x for x in active if first[x]*2 > total]
            if majority:
                trace.append({"active": active[:], "tally": first})
                return result(majority, trace)
        if mode == "coombs":
            tally = dict.fromkeys(active, 0)
            for b in ballots:
                last = next(x for x in reversed(b["ranking"]) if x in tally)
                tally[last] += b["count"]
            worst = best(tally)
        elif mode in {"nanson", "baldwin"}:
            tally = borda_counts(active, ballots)
            worst = best(tally, True)
        else:
            tally = first
            worst = best(tally, True)
        row = {"active": active[:], "tally": tally}
        if len(set(tally.values())) == 1 and (mode == "nanson" or len(active) == 2):
            trace.append(row)
            return result(active, trace)
        if mode == "nanson":
            eliminated = [x for x in active if tally[x]*len(active) <= sum(tally.values())]
        else:
            eliminated = [worst[-1]]
        row["eliminated"] = eliminated
        trace.append(row)
        active = [x for x in active if x not in eliminated]
    trace.append({"active": active[:]})
    return result(active, trace)

def count_nanson(c, ballots, options):
    return elimination(c, ballots, "nanson")

election = {'method': 'nanson', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_nanson(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
