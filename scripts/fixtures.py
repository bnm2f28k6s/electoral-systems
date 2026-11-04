"""Small synthetic profiles shared by the chapters and API examples."""

METHOD_IDS = [
    "plurality", "anti-plurality", "two-round", "instant-runoff", "coombs",
    "nanson", "baldwin", "tideman-alternative", "minimax", "copeland", "black",
    "kemeny-young", "ranked-pairs", "schulze", "borda", "bucklin", "dodgson",
    "approval", "majority-judgment", "score", "star", "quadratic",
    "random-ballot", "maximal-lotteries", "sortition",
]


def example_request(method):
    """One comparable nine-voter profile, encoded in each method's ballot format."""
    ballots = [
        {"ranking": ["A", "B", "C"], "count": 4},
        {"ranking": ["B", "C", "A"], "count": 3},
        {"ranking": ["C", "B", "A"], "count": 2},
    ]
    if method == "dodgson":
        # The exact adjacent-swap search is intentionally limited to eight voters.
        ballots[0]["count"] = 3
        ballots[1]["count"] = 2
    elif method == "approval":
        ballots = [
            {"approvals": ["A", "B"], "count": 4},
            {"approvals": ["B", "C"], "count": 3},
            {"approvals": ["C"], "count": 2},
        ]
    elif method in ("score", "star", "majority-judgment"):
        ballots = [
            {"scores": {"A": 5, "B": 3, "C": 0}, "count": 4},
            {"scores": {"A": 0, "B": 4, "C": 3}, "count": 3},
            {"scores": {"A": 0, "B": 4, "C": 5}, "count": 2},
        ]
    elif method == "quadratic":
        ballots = [
            {"credits": {"A": 5, "B": 3, "C": 0}, "count": 4},
            {"credits": {"A": 0, "B": 4, "C": 3}, "count": 3},
            {"credits": {"A": 0, "B": 4, "C": 5}, "count": 2},
        ]
    elif method == "sortition":
        ballots = []
    return {"method": method, "candidates": ["A", "B", "C"], "ballots": ballots,
            "options": {"maxScore": 5, "budget": 100, "seed": 1}}


# These expectations are calculated independently of either engine.
EXPECTED_WINNERS = {method: ["B"] for method in METHOD_IDS}
EXPECTED_WINNERS.update({"plurality": ["A"], "random-ballot": ["A"], "sortition": ["A"]})
