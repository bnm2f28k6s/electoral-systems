"""Self-contained multi-winner teaching algorithms (Python 3.9+, stdlib).

Supply one JSON election on stdin. Internal/final consequential ties use the
published candidate input priority; every result contains exactly `seats` names.
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
    return isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) <= 9007199254740991 and value % 1 == 0


def validate(request):
    require(isinstance(request, dict), "Request must be an object")
    require(not set(request) - {"method", "candidates", "seats", "ballots", "options"}, "Unknown request field")
    method = request.get("method")
    require(isinstance(method, str) and method in METHODS, "Unknown multi-winner method")
    c = request.get("candidates")
    require(isinstance(c, list) and len(c) >= 1, "Supply at least one candidate")
    require(len(c) <= 32, "At most 32 candidates", 413)
    require(all(isinstance(x, str) and bool(x.strip()) and len(x) <= 100 for x in c), "Candidate IDs must be nonempty strings of at most 100 characters")
    require(len(set(c)) == len(c), "Candidate IDs must be unique")
    seats = request.get("seats")
    require(integer(seats) and 1 <= seats <= len(c), "seats must be an integer from 1 to candidate count")
    seats = int(seats)
    options = request.get("options", {})
    require(isinstance(options, dict), "options must be an object")
    require(not set(options) - {"maxScore", "budget", "limit", "seed"}, "Unknown option")
    options = {"maxScore": 5, "budget": 100, "limit": max(1, seats-1), "seed": 1, **options}
    for key, low, high in [("maxScore", 1, 100), ("budget", 1, 1000000), ("limit", 1, 32), ("seed", 0, 4294967295)]:
        require(integer(options[key]) and low <= options[key] <= high, key + " is outside its integer bounds")
    options = {key: int(value) for key, value in options.items()}
    if method == "limited-vote":
        require(options["limit"] <= max(1, seats-1), "Limited vote limit must be below seats (or 1 for one seat)")
    ballots = request.get("ballots")
    require(isinstance(ballots, list), "ballots must be an array")
    require(len(ballots) <= 10000, "At most 10000 ballot groups", 413)
    require((method == "sortition" and not ballots) or (method != "sortition" and bool(ballots)), "Only sortition accepts an empty ballot array, and sortition requires it")
    expected = {"approval": "approvals", "proportional-approval": "approvals", "sequential-proportional-approval": "approvals", "phragmen": "approvals", "limited-vote": "approvals", "reweighted-range": "scores", "cumulative": "votes"}.get(method, "ranking")
    normalized = []
    total = 0
    for b in ballots:
        require(isinstance(b, dict), "Each ballot must be an object")
        require(not set(b) - {"ranking", "approvals", "choice", "scores", "votes", "count"}, "Unknown ballot field")
        fields = set(b) & {"ranking", "approvals", "choice", "scores", "votes"}
        require(len(fields) == 1, "Each ballot needs exactly one format")
        field = next(iter(fields))
        require(field == expected or (method == "single-non-transferable" and field == "choice"), "Wrong ballot format for " + method)
        count = b.get("count", 1)
        require(integer(count) and 1 <= count <= 1000000, "count must be a positive integer at most 1000000")
        count = int(count)
        total += count
        require(total <= 1000000, "At most 1000000 represented voters", 413)
        value = b[field]
        if field == "ranking":
            require(isinstance(value, list) and len(value) == len(c) and all(isinstance(x, str) for x in value) and set(value) == set(c), "ranking must list every candidate exactly once")
        elif field == "choice":
            require(isinstance(value, str) and value in c, "choice must name a candidate")
        elif field == "approvals":
            require(isinstance(value, list) and all(isinstance(x, str) and x in c for x in value) and len(value) == len(set(value)), "approvals must be a subset without duplicates")
            if method == "limited-vote":
                require(len(value) <= options["limit"], "Too many approvals for limited vote")
        else:
            require(isinstance(value, dict) and set(value) == set(c), field + " must contain every candidate")
            require(all(integer(x) for x in value.values()), field + " must contain integer values")
            require(all(x >= 0 for x in value.values()), field + " values must be nonnegative")
            require(all(x <= options["maxScore"] for x in value.values()) if field == "scores" else sum(value.values()) <= options["budget"], "Scores or cumulative vote budget exceeded")
            value = {key: int(item) for key, item in value.items()}
        normalized.append({field: value, "count": count})
    if method in {"proportional-approval", "minimax-external-opposition"}:
        require(len(c) <= 8, "Exact committee enumeration supports at most 8 candidates", 413)
    if method in {"cpo-stv", "schulze-stv"}:
        require(len(c) <= 6 and len(ballots) <= 100, "Exact STV comparisons support at most 6 candidates and 100 ballot groups", 413)
    return method, c, normalized, seats, options


def ordered(c, elected):
    return [x for x in c if x in elected]


def number_map(tally):
    return {x: float(value) if isinstance(value, Fraction) else value for x, value in tally.items()}


def select_top(c, tally, seats):
    ranked = sorted(c, key=lambda x: -tally[x])
    cutoff = tally[ranked[seats-1]]
    tie = any(tally[x] == cutoff for x in ranked[seats:])
    return ordered(c, ranked[:seats]), tie


def tally_result(c, tally, seats, label="tally"):
    winners, tie = select_top(c, tally, seats)
    return {"winners": winners, "tie": tie, "trace": [{label: number_map(tally)}]}


def pairwise(c, ballots):
    matrix = {x: dict.fromkeys(c, 0) for x in c}
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            for y in b["ranking"][i+1:]:
                matrix[x][y] += b["count"]
    return matrix


def borda_counts(c, ballots):
    tally = dict.fromkeys(c, 0)
    for b in ballots:
        for i, x in enumerate(b["ranking"]):
            tally[x] += (len(c)-i-1)*b["count"]
    return tally


def count_approval(c, ballots, seats, options):
    tally = {x: sum(b["count"] for b in ballots if x in b["approvals"]) for x in c}
    return tally_result(c, tally, seats)


def count_k_borda(c, ballots, seats, options):
    return tally_result(c, borda_counts(c, ballots), seats)


def count_bloc(c, ballots, seats, options):
    tally = {x: sum(b["count"] for b in ballots if x in b["ranking"][:seats]) for x in c}
    return tally_result(c, tally, seats)


def count_single_non_transferable(c, ballots, seats, options):
    tally = dict.fromkeys(c, 0)
    for b in ballots:
        tally[b.get("choice") or b["ranking"][0]] += b["count"]
    return tally_result(c, tally, seats)


def count_limited_vote(c, ballots, seats, options):
    return count_approval(c, ballots, seats, options)


def count_cumulative(c, ballots, seats, options):
    tally = {x: sum(b["votes"][x]*b["count"] for b in ballots) for x in c}
    return tally_result(c, tally, seats)


def committee_optimum(c, committees, scores, minimize=False):
    optimum = (min if minimize else max)(scores)
    tied = [list(committee) for committee, score in zip(committees, scores) if score == optimum]
    return {"winners": tied[0], "tie": len(tied) > 1, "trace": [{"committees": [{"committee": list(committee), "score": float(score) if isinstance(score, Fraction) else score} for committee, score in zip(committees, scores)], "bestScore": float(optimum) if isinstance(optimum, Fraction) else optimum, "tiedCommittees": tied}]}


def count_proportional_approval(c, ballots, seats, options):
    committees = list(itertools.combinations(c, seats))
    harmonic = [sum((Fraction(1, j) for j in range(1, t+1)), Fraction(0)) for t in range(seats+1)]
    scores = [sum((b["count"]*harmonic[sum(x in b["approvals"] for x in committee)] for b in ballots), Fraction(0)) for committee in committees]
    return committee_optimum(c, committees, scores)


def count_sequential_proportional_approval(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        tally = {x: sum((Fraction(b["count"], 1+sum(y in b["approvals"] for y in elected)) for b in ballots if x in b["approvals"]), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}


def count_reweighted_range(c, ballots, seats, options):
    elected, trace, tie = [], [], False
    for step in range(seats):
        weights = [Fraction(options["maxScore"], options["maxScore"]+sum(b["scores"][x] for x in elected)) for b in ballots]
        tally = {x: sum((b["count"]*weight*b["scores"][x] for b, weight in zip(ballots, weights)), Fraction(0)) for x in c if x not in elected}
        high = max(tally.values())
        tied = [x for x in c if x in tally and tally[x] == high]
        elected.append(tied[0])
        tie |= len(tied) > 1
        trace.append({"round": step+1, "weights": [float(w) for w in weights], "tally": number_map(tally), "selected": tied[0], "tied": tied})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}


def count_phragmen(c, ballots, seats, options):
    loads = [Fraction(0) for b in ballots]
    elected, trace, tie = [], [], False
    for step in range(seats):
        levels = {}
        for x in c:
            if x in elected:
                continue
            support = sum(b["count"] for b in ballots if x in b["approvals"])
            levels[x] = (1+sum((load*b["count"] for b, load in zip(ballots, loads) if x in b["approvals"]), Fraction(0)))/support if support else None
        finite = [v for v in levels.values() if v is not None]
        low = min(finite) if finite else None
        tied = [x for x in c if x in levels and levels[x] == low]
        winner = tied[0]
        elected.append(winner)
        tie |= len(tied) > 1
        if low is not None:
            loads = [low if winner in b["approvals"] else load for b, load in zip(ballots, loads)]
        trace.append({"round": step+1, "loadLevels": {x: float(v) if v is not None else None for x, v in levels.items()}, "selected": winner, "tied": tied, "loads": [float(v) for v in loads]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}


def count_minimax(c, ballots, seats, options):
    matrix = pairwise(c, ballots)
    total = sum(b["count"] for b in ballots)
    tally = {x: min([matrix[x][y] for y in c if y != x] or [total]) for x in c}
    counted = tally_result(c, tally, seats, "simpsonScores")
    counted["trace"].insert(0, {"pairwise": matrix})
    return counted


def count_minimax_external_opposition(c, ballots, seats, options):
    matrix = pairwise(c, ballots)
    total = sum(b["count"] for b in ballots)
    committees = list(itertools.combinations(c, seats))
    scores = [min([matrix[x][y] for x in committee for y in c if y not in committee] or [total]) for committee in committees]
    counted = committee_optimum(c, committees, scores)
    counted["trace"].insert(0, {"pairwise": matrix})
    return counted


def droop_fraction(total, seats):
    return Fraction(total, seats+1) + Fraction(1, (seats+1)**2)


def count_expanding_approvals(c, ballots, seats, options):
    quota = droop_fraction(sum(b["count"] for b in ballots), seats)
    rank_vectors = {x: tuple(sum(b["count"] for b in ballots if b["ranking"][depth] == x) for depth in range(len(c))) for x in c}
    priority = sorted(c, key=lambda x: tuple(-n for n in rank_vectors[x]))
    weights = [Fraction(b["count"]) for b in ballots]
    elected, depth, tie = [], 1, False
    trace = [{"quota": float(quota), "priority": priority, "rankVectors": {x: list(v) for x, v in rank_vectors.items()}}]
    while len(elected) < seats:
        tally = {x: sum((w for b, w in zip(ballots, weights) if x in b["ranking"][:depth]), Fraction(0)) for x in c if x not in elected}
        eligible = [x for x in priority if x in tally and tally[x] >= quota]
        if not eligible:
            trace.append({"depth": depth, "tally": number_map(tally), "eligible": []})
            depth += 1
            continue
        winner = eligible[0]
        tied = [x for x in eligible if rank_vectors[x] == rank_vectors[winner]]
        tie |= len(tied) > 1
        elected.append(winner)
        factor = (tally[winner]-quota)/tally[winner]
        weights = [w*factor if winner in b["ranking"][:depth] else w for b, w in zip(ballots, weights)]
        trace.append({"depth": depth, "tally": number_map(tally), "eligible": eligible, "selected": winner, "tied": tied, "remainingWeights": [float(w) for w in weights]})
    return {"winners": ordered(c, elected), "tie": tie, "trace": trace}


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


def count_sortition(c, ballots, seats, options):
    active, elected, trace, seed = c[:], [], [], options["seed"]
    for step in range(seats):
        winner, seed, probabilities = draw(active, dict.fromkeys(active, 1), seed)
        elected.append(winner)
        active.remove(winner)
        trace.append({"round": step+1, "probabilities": probabilities, "selected": winner, "state": seed})
    return {"winners": ordered(c, elected), "tie": False, "trace": trace}


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


METHODS = {
    "approval": count_approval,
    "proportional-approval": count_proportional_approval,
    "sequential-proportional-approval": count_sequential_proportional_approval,
    "reweighted-range": count_reweighted_range,
    "stv": count_stv,
    "cpo-stv": count_cpo_stv,
    "schulze-stv": count_schulze_stv,
    "phragmen": count_phragmen,
    "k-borda": count_k_borda,
    "bloc": count_bloc,
    "quota-borda": count_quota_borda,
    "expanding-approvals": count_expanding_approvals,
    "minimax": count_minimax,
    "minimax-external-opposition": count_minimax_external_opposition,
    "single-non-transferable": count_single_non_transferable,
    "limited-vote": count_limited_vote,
    "cumulative": count_cumulative,
    "sortition": count_sortition,
    "multiple-random-ballots": count_multiple_random_ballots,
}


def simulate(request):
    method, c, ballots, seats, options = validate(request)
    counted = METHODS[method](c, ballots, seats, options)
    return {"method": method, "seats": seats, **counted}


def reject_constant(value):
    raise ElectionError("JSON numbers must be finite")


if __name__ == "__main__":
    try:
        print(json.dumps(simulate(json.load(sys.stdin, parse_constant=reject_constant)), ensure_ascii=False, allow_nan=False))
    except (ElectionError, json.JSONDecodeError, RecursionError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        sys.exit(1)
