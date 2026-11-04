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

def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]

def solve_linear(matrix, rhs):
    n = len(rhs)
    augmented = [[Fraction(x) for x in row] + [Fraction(value)] for row, value in zip(matrix, rhs)]
    for column in range(n):
        pivot = next((row for row in range(column, n) if augmented[row][column]), None)
        if pivot is None:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value/divisor for value in augmented[column]]
        for row in range(n):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a-factor*b for a, b in zip(augmented[row], augmented[column])]
    return [row[-1] for row in augmented]

def count_maximal_lotteries(c, ballots, options):
    p = pairwise(c, ballots)
    n = len(c)
    margins = [[p[x][y]-p[y][x] for y in c] for x in c]
    # Vertices of {q>=0, sum(q)=1, q^T margins>=0}. A maximal lottery is
    # a minimax strategy of this skew-symmetric zero-sum game (value zero).
    constraints = [[int(i == j) for i in range(n)] for j in range(n)]
    constraints += [[margins[i][j] for i in range(n)] for j in range(n)]
    probabilities = None
    for active in itertools.combinations(range(2*n), n-1):
        solution = solve_linear([[1]*n] + [constraints[i] for i in active], [1]+[0]*(n-1))
        if solution is not None and all(x >= 0 for x in solution) and all(sum(solution[i]*margins[i][j] for i in range(n)) >= 0 for j in range(n)):
            probabilities = solution
            break
    if probabilities is None:
        raise RuntimeError("Maximal-lottery feasibility invariant failed")
    lottery = [{"candidate": x, "probability": float(probabilities[i])} for i, x in enumerate(c)]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"pairwise": p}, {"margins": margins, "seed": options["seed"]}], lottery=lottery)

election = {'method': 'maximal-lotteries', 'candidates': ['A', 'B', 'C'], 'ballots': [{'ranking': ['A', 'B', 'C'], 'count': 4}, {'ranking': ['B', 'C', 'A'], 'count': 3}, {'ranking': ['C', 'B', 'A'], 'count': 2}], 'options': {'maxScore': 5, 'budget': 100, 'seed': 1}}
counted = count_maximal_lotteries(election["candidates"], election["ballots"], election["options"])
answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}
print(json.dumps(answer, indent=2))
