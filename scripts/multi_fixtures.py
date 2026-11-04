"""Synthetic committee profiles with explicit ballot information for each rule."""

METHOD_IDS = [
    "approval", "proportional-approval", "sequential-proportional-approval",
    "reweighted-range", "stv", "cpo-stv", "schulze-stv", "phragmen", "k-borda",
    "bloc", "quota-borda", "expanding-approvals", "minimax",
    "minimax-external-opposition", "single-non-transferable", "limited-vote",
    "cumulative", "sortition", "multiple-random-ballots",
]

APPROVAL_METHODS = {"approval", "proportional-approval", "sequential-proportional-approval", "phragmen", "limited-vote"}


def example_request(method):
    ballots = [
        {"ranking": ["A", "B", "C", "D"], "count": 6},
        {"ranking": ["C", "D", "A", "B"], "count": 3},
        {"ranking": ["D", "C", "B", "A"], "count": 1},
    ]
    if method in APPROVAL_METHODS:
        ballots = [
            {"approvals": ["A", "B"], "count": 6},
            {"approvals": ["C", "D"], "count": 3},
            {"approvals": ["D"], "count": 1},
        ]
        if method == "limited-vote":
            ballots = [
                {"approvals": ["A"], "count": 6},
                {"approvals": ["C"], "count": 3},
                {"approvals": ["D"], "count": 1},
            ]
    elif method == "reweighted-range":
        ballots = [
            {"scores": {"A": 5, "B": 4, "C": 0, "D": 0}, "count": 6},
            {"scores": {"A": 0, "B": 0, "C": 5, "D": 4}, "count": 3},
            {"scores": {"A": 0, "B": 0, "C": 4, "D": 5}, "count": 1},
        ]
    elif method == "cumulative":
        ballots = [
            {"votes": {"A": 60, "B": 40, "C": 0, "D": 0}, "count": 6},
            {"votes": {"A": 0, "B": 0, "C": 60, "D": 40}, "count": 3},
            {"votes": {"A": 0, "B": 0, "C": 0, "D": 100}, "count": 1},
        ]
    elif method == "sortition":
        ballots = []
    return {"method": method, "seats": 2, "candidates": ["A", "B", "C", "D"],
            "ballots": ballots, "options": {"maxScore": 5, "budget": 100, "limit": 1, "seed": 1}}


# Expected committees will be checked from hand calculations, not derived from
# either engine. Keep these explicit when the documented profile changes.
EXPECTED_WINNERS = {
    "approval": ["A", "B"],
    "proportional-approval": ["A", "D"],
    "sequential-proportional-approval": ["A", "D"],
    "reweighted-range": ["A", "C"],
    "stv": ["A", "C"],
    "cpo-stv": ["A", "C"],
    "schulze-stv": ["A", "C"],
    "phragmen": ["A", "D"],
    "k-borda": ["A", "C"],
    "bloc": ["A", "B"],
    "quota-borda": ["A", "C"],
    "expanding-approvals": ["A", "C"],
    "minimax": ["A", "C"],
    "minimax-external-opposition": ["A", "B"],
    "single-non-transferable": ["A", "C"],
    "limited-vote": ["A", "C"],
    "cumulative": ["A", "B"],
    "sortition": ["A", "C"],
    "multiple-random-ballots": ["A", "B"],
}

EXAMPLE_EXPLANATIONS = {
    "approval": "A and B each receive six approvals; D receives four and C three. The two highest totals elect A and B. This count does not reduce the influence of voters who already helped elect somebody.",
    "proportional-approval": "Electing A and B gives the six shared supporters 1 + 1/2 points each, for nine points total. A and D instead give each of the ten voters one approved representative, for ten points. B and D also score ten; the fixed candidate priority selects A and D.",
    "sequential-proportional-approval": "A and B initially tie with six approvals. Priority selects A. Those six voters then contribute only half a point to B, giving B three points. D still has four, so D takes the second seat.",
    "reweighted-range": "Initial score totals are A 30, B 24, C 19, D 17. A wins the first seat. Its six supporters then have half weight: B falls to 12 while C retains 19. The second seat goes to C.",
    "stv": "The integer Droop quota is four. A starts with six votes, keeps four, and transfers a surplus of two to B. D has only one vote and is eliminated; that ballot transfers to C, who now has four and takes the second seat.",
    "cpo-stv": "For the comparison of A–C against A–B, D is excluded and its ballot goes to C. Common member A keeps its quota of four and transfers two votes to B. The totals for the two committees are eight for A–C and six for A–B. Comparing all committees selects A–C.",
    "schulze-stv": "Compare A–C with A–B. Against outsider B, four voters can support C and nine can support A; all ten can support at least one of A or C. The largest equally shared support is min(9, 4, 10/2) = 4. In the reverse direction, only the six majority voters can support A or B above C, so the equal support is 6/2 = 3. The full strongest-path comparison selects A–C.",
    "phragmen": "A and B each have six supporters, so either can spread one seat's load over six voters. Priority selects A. A second seat for B would bring those same voters to load 1/3 each, while D can spread it over four previously uncharged voters at load 1/4. D takes the second seat.",
    "k-borda": "With three, two, one, and zero points per ranking, the totals are A 21, B 13, C 17, D 9. The two largest totals elect A and C.",
    "bloc": "The first six voters support their top two candidates, A and B. The other four support C and D. Totals of six, six, four, and four elect A and B, giving both seats to the larger group.",
    "quota-borda": "The exact quota is 31/9. The six A-first voters earn a seat for A. At depth two, the four voters sharing the top set C–D also earn one seat. C has more Borda points than D, so the committee is A–C.",
    "expanding-approvals": "The exact quota is 31/9. A qualifies at depth one. Spending that quota leaves A's supporters with total weight 23/9. At depth two the C–D group still has weight four and qualifies; the rank-based priority chooses C.",
    "minimax": "A's weakest head-to-head support is six voters, C's is four, and B's and D's are one each. Choosing the two strongest individual worst-case totals elects A and C.",
    "minimax-external-opposition": "For committee A–B, every member has at least six supporters against every outsider. A–C and C–D have worst support four, and each other committee has worst support one. The best worst-case committee is A–B.",
    "single-non-transferable": "Only first choices count: A has six, C three, D one, and B zero. A and C take the two seats; nobody's unused support transfers.",
    "limited-vote": "Each voter can mark at most one candidate in this two-seat example. A receives six marks, C three, and D one, so A and C win. Approvals here are supplied explicitly rather than inferred from a ranking.",
    "cumulative": "Adding the submitted vote allocations gives A 360, B 240, C 180, and D 220. A and B have the highest totals. Each voter spends at most the same 100-vote budget.",
    "sortition": "With seed one, the first uniform draw selects A. The second uniform draw from B, C, and D selects C. Every two-candidate committee has the same mathematical probability; these two names are one reproducible sample.",
    "multiple-random-ballots": "With seed one, both independent ballot draws select a ballot from the six-voter A–B group. The first draw elects A; the next elects that ballot's highest remaining candidate, B. Other seeds can choose different committees.",
}
