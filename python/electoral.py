"""Self-contained single-winner teaching algorithms (Python 3.9+, stdlib only).

Run: echo '{"method":"plurality","candidates":["A","B"],"ballots":[{"choice":"A"}]}' | python3 python/electoral.py
The candidates array is a fixed priority: earlier candidates survive internal ties.
Final equal tallies remain co-winners. Complete strict rankings are required.
"""
import itertools
import json
import sys
from fractions import Fraction


class ElectionError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def require(condition, message, status=400):
    if not condition:
        raise ElectionError(message, status)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate(request):
    require(isinstance(request, dict), "Request must be an object")
    require(not set(request) - {"method", "candidates", "ballots", "options"}, "Unknown request field")
    method = request.get("method")
    require(isinstance(method, str) and method in METHODS, "Unknown method")
    c = request.get("candidates")
    require(isinstance(c, list) and len(c) >= 1, "Supply at least one candidate")
    require(len(c) <= 32, "At most 32 candidates", 413)
    require(all(isinstance(x, str) and bool(x.strip()) and len(x) <= 100 for x in c), "Candidate IDs must be nonempty strings of at most 100 characters")
    require(len(c) == len(set(c)), "Candidate IDs must be unique")
    options = request.get("options", {})
    require(isinstance(options, dict), "options must be an object")
    require(not set(options) - {"maxScore", "budget", "seed"}, "Unknown option")
    options = {"maxScore": 5, "budget": 100, "seed": 1, **options}
    require(integer(options["maxScore"]) and 1 <= options["maxScore"] <= 100, "maxScore must be an integer from 1 to 100")
    require(integer(options["budget"]) and 1 <= options["budget"] <= 1000000, "budget must be an integer from 1 to 1000000")
    require(integer(options["seed"]) and 0 <= options["seed"] < 2**32, "seed must be a uint32 integer")
    ballots = request.get("ballots")
    require(isinstance(ballots, list), "ballots must be an array")
    require(len(ballots) <= 10000, "At most 10000 ballot groups", 413)
    require(method == "sortition" or len(ballots) > 0, "At least one ballot is required")
    require(method != "sortition" or len(ballots) == 0, "Sortition accepts no ballots")
    normalized = []
    total = 0
    for b in ballots:
        require(isinstance(b, dict), "Each ballot must be an object")
        require(not set(b) - {"ranking", "choice", "approvals", "scores", "credits", "count"}, "Unknown ballot field")
        fields = set(b) & {"ranking", "choice", "approvals", "scores", "credits"}
        require(len(fields) == 1, "Each ballot needs exactly one ballot format")
        count = b.get("count", 1)
        require(integer(count) and 1 <= count <= 1000000, "count must be a positive integer at most 1000000")
        total += count
        require(total <= 1000000, "At most 1000000 represented voters", 413)
        field = next(iter(fields))
        allowed = {"approval": {"approvals"}, "score": {"scores"}, "star": {"scores"}, "majority-judgment": {"scores"}, "quadratic": {"credits"}, "plurality": {"ranking", "choice"}, "anti-plurality": {"ranking", "choice"}, "random-ballot": {"ranking", "choice"}}.get(method, {"ranking"})
        require(field in allowed, "Wrong ballot format for " + method)
        value = b[field]
        if field == "ranking":
            require(isinstance(value, list) and len(value) == len(c) and all(isinstance(x, str) for x in value) and set(value) == set(c), "ranking must list every candidate exactly once")
        elif field == "choice":
            require(isinstance(value, str) and value in c, "choice must name a candidate")
        elif field == "approvals":
            require(isinstance(value, list) and all(isinstance(x, str) and x in c for x in value) and len(value) == len(set(value)), "approvals must be a subset without duplicates")
        else:
            require(isinstance(value, dict) and set(value) == set(c), field + " must contain every candidate exactly once")
            require(all(integer(x) for x in value.values()), field + " values must be integers")
            if field == "scores":
                require(all(0 <= x <= options["maxScore"] for x in value.values()), "Scores outside 0..maxScore")
            else:
                require(sum(x*x for x in value.values()) <= options["budget"], "Quadratic ballot exceeds sum-of-squares budget")
        normalized.append({field: value, "count": count})
    if method == "kemeny-young":
        require(len(c) <= 8, "Exact Kemeny enumeration supports at most 8 candidates", 413)
    if method == "dodgson":
        require(len(c) <= 5 and total <= 8, "Exact Dodgson supports at most 5 candidates and 8 represented voters", 413)
    if method == "maximal-lotteries":
        require(len(c) <= 6, "Exact maximal-lottery vertex enumeration supports at most 6 candidates", 413)
    return method, c, normalized, options


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


def condorcet(c, p):
    return [x for x in c if all(x == y or p[x][y] > p[y][x] for y in c)]


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


def count_plurality(c, ballots, options):
    tally = first_counts(c, ballots)
    return result(best(tally), [{"tally": tally}])


def count_anti_plurality(c, ballots, options):
    tally = dict.fromkeys(c, 0)
    for b in ballots:
        tally[b.get("choice") or b["ranking"][-1]] += b["count"]
    return result(best(tally, True), [{"vetoes": tally}])


def count_two_round(c, ballots, options):
    first = first_counts(c, ballots)
    total = sum(first.values())
    trace = [{"round": 1, "tally": first}]
    leaders = best(first)
    if len(c) == 1 or any(first[x]*2 > total for x in c):
        return result(leaders, trace)
    finalists = sorted(c, key=lambda x: -first[x])[:2]
    tally = first_counts(finalists, ballots)
    trace.append({"round": 2, "active": finalists, "tally": tally})
    return result([x for x in c if x in best(tally)], trace)


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
        if len(set(tally.values())) == 1:
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


def count_instant_runoff(c, ballots, options):
    return elimination(c, ballots, "instant-runoff")


def count_coombs(c, ballots, options):
    return elimination(c, ballots, "coombs")


def count_nanson(c, ballots, options):
    return elimination(c, ballots, "nanson")


def count_baldwin(c, ballots, options):
    return elimination(c, ballots, "baldwin")


def count_tideman_alternative(c, ballots, options):
    return elimination(c, ballots, "tideman-alternative")


def count_borda(c, ballots, options):
    tally = borda_counts(c, ballots)
    return result(best(tally), [{"tally": tally}])


def count_minimax(c, ballots, options):
    p = pairwise(c, ballots)
    tally = {x: max([0] + [p[y][x]-p[x][y] for y in c if y != x]) for x in c}
    return result(best(tally, True), [{"pairwise": p}, {"worstDefeat": tally}])


def count_copeland(c, ballots, options):
    p = pairwise(c, ballots)
    tally = {x: sum(1 if p[x][y] > p[y][x] else .5 if p[x][y] == p[y][x] else 0 for y in c if y != x) for x in c}
    return result(best(tally), [{"pairwise": p}, {"tally": tally}])


def count_black(c, ballots, options):
    p = pairwise(c, ballots)
    winners = condorcet(c, p)
    if winners:
        return result(winners, [{"pairwise": p}, {"condorcet": winners}])
    fallback = count_borda(c, ballots, options)
    return result(fallback["winners"], [{"pairwise": p}, {"fallback": "borda"}] + fallback["trace"])


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


def count_schulze(c, ballots, options):
    p = pairwise(c, ballots)
    paths = {x: {y: p[x][y] if x != y and p[x][y] > p[y][x] else 0 for y in c} for x in c}
    for middle in c:
        for start in c:
            for end in c:
                if len({start, middle, end}) == 3:
                    paths[start][end] = max(paths[start][end], min(paths[start][middle], paths[middle][end]))
    winners = [x for x in c if all(paths[x][y] >= paths[y][x] for y in c)]
    return result(winners, [{"pairwise": p}, {"strongestPaths": paths}])


def count_bucklin(c, ballots, options):
    tally = dict.fromkeys(c, 0)
    total = sum(b["count"] for b in ballots)
    trace = []
    for depth in range(len(c)):
        for b in ballots:
            tally[b["ranking"][depth]] += b["count"]
        trace.append({"depth": depth+1, "tally": tally.copy()})
        if max(tally.values())*2 > total:
            return result(best(tally), trace)
    return result(best(tally), trace)


def count_dodgson(c, ballots, options):
    p = pairwise(c, ballots)
    rankings = [b["ranking"] for b in ballots for _ in range(b["count"])]
    threshold = len(rankings)//2 + 1
    tally = {}
    for target in c:
        opponents = [x for x in c if x != target]
        needed = tuple(max(0, threshold-p[target][x]) for x in opponents)
        states = {tuple(0 for _ in opponents): 0}
        for ranking in rankings:
            position = ranking.index(target)
            choices = []
            for swaps in range(position+1):
                passed = set(ranking[position-swaps:position])
                choices.append((swaps, tuple(int(x in passed) for x in opponents)))
            updated = {}
            for gains, cost in states.items():
                for swaps, extra in choices:
                    new = tuple(min(needed[i], gains[i]+extra[i]) for i in range(len(opponents)))
                    updated[new] = min(updated.get(new, float("inf")), cost+swaps)
            states = updated
        tally[target] = states[needed]
    return result(best(tally, True), [{"pairwise": p}, {"adjacentSwaps": tally}])


def count_approval(c, ballots, options):
    tally = {x: sum(b["count"] for b in ballots if x in b["approvals"]) for x in c}
    return result(best(tally), [{"tally": tally}])


def count_score(c, ballots, options):
    tally = {x: sum(b["scores"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally}])


def count_star(c, ballots, options):
    tally = {x: sum(b["scores"][x]*b["count"] for b in ballots) for x in c}
    finalists = sorted(c, key=lambda x: -tally[x])[:2]
    trace = [{"stage": "score", "tally": tally, "finalists": finalists}]
    if len(finalists) == 1:
        return result(finalists, trace)
    a, b = finalists
    runoff = {a: sum(v["count"] for v in ballots if v["scores"][a] > v["scores"][b]), b: sum(v["count"] for v in ballots if v["scores"][b] > v["scores"][a])}
    trace.append({"stage": "runoff", "tally": runoff})
    return result([x for x in c if x in best(runoff)], trace)


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


def count_quadratic(c, ballots, options):
    # credits records signed voice votes; the budget charges their squares.
    tally = {x: sum(b["credits"][x]*b["count"] for b in ballots) for x in c}
    return result(best(tally), [{"tally": tally, "budget": options["budget"]}])


def draw(lottery, seed):
    state = (1664525*seed + 1013904223) % (2**32)
    threshold = state / (2**32)
    cumulative = 0
    for row in lottery:
        cumulative += row["probability"]
        if threshold < cumulative:
            return row["candidate"]
    return lottery[-1]["candidate"]


def count_random_ballot(c, ballots, options):
    tally = first_counts(c, ballots)
    total = sum(tally.values())
    lottery = [{"candidate": x, "probability": tally[x]/total} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"tally": tally, "seed": options["seed"]}], lottery=lottery)


def count_sortition(c, ballots, options):
    lottery = [{"candidate": x, "probability": 1/len(c)} for x in c]
    winner = draw(lottery, options["seed"])
    return result([winner], [{"seed": options["seed"]}], lottery=lottery)


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


METHODS = {
    "plurality": count_plurality, "anti-plurality": count_anti_plurality,
    "two-round": count_two_round, "instant-runoff": count_instant_runoff,
    "coombs": count_coombs, "nanson": count_nanson, "baldwin": count_baldwin,
    "tideman-alternative": count_tideman_alternative, "minimax": count_minimax,
    "copeland": count_copeland, "black": count_black, "kemeny-young": count_kemeny_young,
    "ranked-pairs": count_ranked_pairs, "schulze": count_schulze, "borda": count_borda,
    "bucklin": count_bucklin, "dodgson": count_dodgson, "approval": count_approval,
    "majority-judgment": count_majority_judgment, "score": count_score, "star": count_star,
    "quadratic": count_quadratic, "random-ballot": count_random_ballot,
    "maximal-lotteries": count_maximal_lotteries, "sortition": count_sortition,
}


def simulate(request):
    method, c, ballots, options = validate(request)
    counted = METHODS[method](c, ballots, options)
    return {"method": method, "winners": counted["winners"], "tie": len(counted["winners"]) > 1, "trace": counted["trace"], **({"lottery": counted["lottery"]} if "lottery" in counted else {})}


if __name__ == "__main__":
    try:
        print(json.dumps(simulate(json.load(sys.stdin)), ensure_ascii=False))
    except (ElectionError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        sys.exit(1)
