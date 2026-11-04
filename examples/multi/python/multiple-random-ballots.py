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

def draw(c, tally, seed):
    state = (1664525*seed+1013904223) % 2**32
    total = sum(tally.values())
    threshold, cumulative = Fraction(state, 2**32), Fraction(0)
    probabilities = {x: Fraction(tally[x], total) for x in c}
    for x in c:
        cumulative += probabilities[x]
        if threshold < cumulative:
            return x, state, number_map(probabilities)
    return c[-1], state, number_map(probabilities)

def count_multiple_random_ballots(c, ballots, seats, options):
    active, elected, trace, seed = c[:], [], [], options["seed"]
    for step in range(seats):
        tally = dict.fromkeys(active, 0)
        for b in ballots:
            tally[next(x for x in b["ranking"] if x in active)] += b["count"]
        winner, seed, probabilities = draw(active, tally, seed)
        elected.append(winner)
        active.remove(winner)
        trace.append({"round": step+1, "tally": tally, "probabilities": probabilities, "selected": winner, "state": seed})
    return {"winners": ordered(c, elected), "tie": False, "trace": trace}

election = {'method': 'multiple-random-ballots', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_multiple_random_ballots(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
