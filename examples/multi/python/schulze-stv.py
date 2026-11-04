# Python 3.9+. Save as example.py and run: python3 example.py
# Complete count for valid input. The API performs full validation.
import itertools
import json
import sys
from fractions import Fraction

def pairwise(c, ballots):
    matrix = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                matrix[x][y] += b["count"]
    return matrix

def schulze_strength(committee, outsider, ballots):
    # Weighted Hall inequalities for assigning equal support to each member:
    # t*|S| <= weight of voters preferring some member of S to the outsider.
    strength = None
    for size in range(1, len(committee)+1):
        for subset in itertools.combinations(committee, size):
            support = sum(b["count"] for b in ballots if any(b["ranking"].index(x) < b["ranking"].index(outsider) for x in subset))
            value = Fraction(support, size)
            strength = value if strength is None else min(strength, value)
    return strength

def count_schulze_stv(c, ballots, seats, options):
    committees = list(itertools.combinations(c, seats))
    n = len(committees)
    links = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for i, first in enumerate(committees):
        for j, second in enumerate(committees):
            outsiders = [x for x in second if x not in first]
            if len(outsiders) == 1:
                links[i][j] = schulze_strength(first, outsiders[0], ballots)
    paths = [row[:] for row in links]
    for middle in range(n):
        for start in range(n):
            for end in range(n):
                if len({middle, start, end}) == 3:
                    paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
    stage_two = [list(committees[i]) for i in range(n) if all(paths[i][j] >= paths[j][i] for j in range(n))]
    # The published rule has a third stage: a committee can disqualify another
    # tied committee using the strict single-winner Schulze relation.
    single = pairwise(c, ballots)
    for middle in c:
        for start in c:
            for end in c:
                if len({middle, start, end}) == 3:
                    single[start][end] = max(single[start][end], min(single[start][middle], single[middle][end]))
    tied = [second for second in stage_two if not any(
        any(all(single[a][b] > single[b][a] for b in second if b not in first)
            for a in first if a not in second)
        for first in stage_two if first != second)]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [list(x) for x in committees], "links": [[float(v) for v in row] for row in links], "strongestPaths": [[float(v) for v in row] for row in paths], "stageTwoCommittees": stage_two, "singleWinnerPaths": single, "tiedCommittees": tied}]}

election = {'method': 'schulze-stv', 'candidates': ['A', 'B', 'C', 'D'], 'ballots': [{'ranking': ['A', 'B', 'C', 'D'], 'count': 6}, {'ranking': ['C', 'D', 'A', 'B'], 'count': 3}, {'ranking': ['D', 'C', 'B', 'A'], 'count': 1}], 'seats': 2, 'options': {'maxScore': 5, 'budget': 100, 'limit': 1, 'seed': 1}}
counted = count_schulze_stv(election["candidates"], election["ballots"], election["seats"], election["options"])
answer = {"method": election["method"], "seats": election["seats"], **counted}
print(json.dumps(answer, indent=2))
