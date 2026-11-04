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

def count_stv(c, ballots, seats, options):
    quota = sum(b["count"] for b in ballots)//(seats+1)+1
    weights = [Fraction(b["count"]) for b in ballots]
    active, elected, trace, tie = c[:], [], [{"quota": quota}], False
    while len(elected) < seats:
        if len(active) == seats-len(elected):
            elected.extend(active)
            trace.append({"electedRemaining": active[:]})
            break
        choices = [next(x for x in b["ranking"] if x in active) for b in ballots]
        tally = {x: sum((w for choice, w in zip(choices, weights) if choice == x), Fraction(0)) for x in active}
        eligible = [x for x in active if tally[x] >= quota]
        if eligible:
            high = max(tally[x] for x in eligible)
            tied = [x for x in eligible if tally[x] == high]
            winner = tied[0]
            tie |= len(tied) > 1
            factor = (tally[winner]-quota)/tally[winner]
            weights = [w*factor if choice == winner else w for choice, w in zip(choices, weights)]
            elected.append(winner)
            active.remove(winner)
            trace.append({"tally": number_map(tally), "elected": winner, "tied": tied, "transferFactor": float(factor)})
        else:
            low = min(tally.values())
            tied = [x for x in active if tally[x] == low]
            loser = tied[-1]
            tie |= len(tied) > 1
            active.remove(loser)
            trace.append({"tally": number_map(tally), "eliminated": loser, "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}

election = {'method': 'stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
