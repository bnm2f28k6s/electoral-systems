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

def count_majority_judgment(c, ballots, options):
    histograms = {x: [sum(b["count"] for b in ballots if b["scores"][x] == grade) for grade in range(options["maxScore"]+1)] for x in c}
    def median(histogram):
        position = (sum(histogram)-1)//2
        cumulative = 0
        for grade, count in enumerate(histogram):
            cumulative += count
            if cumulative > position:
                return grade
        return -1
    initial = {x: median(histograms[x]) for x in c}
    trace = [{"majorityGrades": initial, "histograms": {x: h[:] for x, h in histograms.items()}}]
    active = best(initial)
    removed = 0
    while len(active) > 1 and sum(histograms[active[0]]) > 0:
        # One lower median removed per tied candidate per iteration.
        # Equal histograms can never separate; stop without expanding voters.
        if all(histograms[x] == histograms[active[0]] for x in active):
            break
        batch = min(min(sum(histograms[x])-1-2*sum(histograms[x][:median(histograms[x])]),
                            2*sum(histograms[x][:median(histograms[x])])+2*histograms[x][median(histograms[x])]-sum(histograms[x]))+1 for x in active)
        for x in active:
            histograms[x][median(histograms[x])] -= batch
        removed += batch
        grades = {x: median(histograms[x]) for x in active}
        active = best(grades)
    trace.append({"medianGradesRemoved": removed, "remaining": active})
    return result(active, trace)

election = {'method': 'majority-judgment', 'candidates': ['A', 'B', 'C'], 'ballots': [{'scores': {'A': 5, 'B': 3, 'C': 0}, 'count': 4}, {'scores': {'A': 0, 'B': 4, 'C': 3}, 'count': 3}, {'scores': {'A': 0, 'B': 4, 'C': 5}, 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_majority_judgment(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
