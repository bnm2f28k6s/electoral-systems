# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def committee_optimum(c, committees, scores, minimize=False):
    optimum = (min if minimize else max)(scores)
    tied = [list(committee) for committee, score in zip(committees, scores) if score == optimum]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [{"committee": list(committee), "score": float(score) if isinstance(score, Fraction) else score} for committee, score in zip(committees, scores)], "bestScore": float(optimum) if isinstance(optimum, Fraction) else optimum, "tiedCommittees": tied}]}

def cpo_support(c, ballots, first, second, quota, decisions=None):
    active = [x for x in c if x in first or x in second]
    common = [x for x in c if x in first and x in second]
    weights = [Fraction(b["count"]) for b in ballots]
    retained = Fraction(0)
    while True:
        choices = [next(x for x in b["ranking"] if x in active) for b in ballots]
        tally = {x: sum((w for choice, w in zip(choices, weights) if choice == x), Fraction(0)) for x in active}
        eligible = [x for x in common if x in active and tally[x] > quota]
        if not eligible:
            break
        high = max(tally[x] for x in eligible)
        tied = [x for x in eligible if tally[x] == high]
        winner = tied[0]
        if decisions is not None and len(tied) > 1:
            decisions.append({"candidates": tied, "selected": winner})
        factor = (tally[winner]-quota)/tally[winner]
        weights = [w*factor if choice == winner else w for choice, w in zip(choices, weights)]
        retained += quota
        active.remove(winner)
    return retained+sum(tally[x] for x in active if x in first), retained+sum(tally[x] for x in active if x in second)

def count_cpo_stv(c, ballots, seats, options):
    committees = list(itertools.combinations(c, seats))
    quota = sum(b["count"] for b in ballots)//(seats+1)+1
    support = [[Fraction(0) for second in committees] for first in committees]
    comparison_ties = []
    for i, first in enumerate(committees):
        for j in range(i+1, len(committees)):
            decisions = []
            support[i][j], support[j][i] = cpo_support(c, ballots, first, committees[j], quota, decisions)
            if decisions:
                comparison_ties.append({"first": list(first), "second": list(committees[j]), "decisions": decisions})
    worst = [max([Fraction(0)]+[support[j][i]-support[i][j] for j in range(len(committees)) if i != j]) for i in range(len(committees))]
    counted = committee_optimum(c, committees, worst, True)
    counted["tie"] |= bool(comparison_ties)
    counted["trace"].insert(0, {"quota": quota, "support": [[float(value) for value in row] for row in support], "comparisonTies": comparison_ties})
    return counted

election = {'method': 'cpo-stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_cpo_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
