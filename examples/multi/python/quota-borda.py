# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def ordered(c, elected):
    return [x for x in c if x in elected]

def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            tally[x] += (len(c)-i-1)*b["count"]
    return tally

def droop_fraction(total, seats):
    return Fraction(total, seats+1) + Fraction(1, (seats+1)**2)

def count_quota_borda(c, ballots, seats, options):
    quota = droop_fraction(sum(b["count"] for b in ballots), seats)
    borda = borda_counts(c, ballots)
    elected, trace, tie = [], [{"quota": float(quota), "borda": borda}], False
    for depth in range(1, len(c)+1):
        groups = {}
        for b in ballots:
            prefix = tuple(x for x in c if x in b["ranking"][:depth])
            groups[prefix] = groups.get(prefix, 0)+b["count"]
        while len(elected) < seats:
            unmet = [(group, min(len(group), int(Fraction(count)/quota))) for group, count in groups.items() if sum(x in elected for x in group) < min(len(group), int(Fraction(count)/quota))]
            if not unmet:
                break
            eligible = [x for x in c if x not in elected and any(x in group for group, demand in unmet)]
            high = max(borda[x] for x in eligible)
            tied = [x for x in eligible if borda[x] == high]
            elected.append(tied[0])
            tie |= len(tied) > 1
            trace.append({"depth": depth, "demands": [{"candidates": list(group), "seats": demand} for group, demand in unmet], "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'quota-borda', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_quota_borda(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
