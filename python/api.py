"""Ballot-format dispatch over the canonical counting engines.

Family checks constrain format and method only. Engines own all validation,
resource limits, normalization, and counting. Legacy mixed-format profiles keep
using the engine directly through the common facade.
"""
from electoral import METHODS, ElectionError, simulate
from multi_winner import METHODS as MULTI_METHODS
from multi_winner import ElectionError as MultiElectionError, simulate as simulate_multi

FIELDS = {"ranked": "ranking", "marked": "choice", "approval": "approvals",
          "scored": "scores", "quadratic": "credits", "cumulative": "votes", "none": None}
MARKED = ("plurality", "anti-plurality", "random-ballot")
SCORED = ("score", "star", "majority-judgment")
MULTI_APPROVAL = ("approval", "proportional-approval", "sequential-proportional-approval", "phragmen", "limited-vote")
FAMILY_METHODS = {
    "ranked": tuple(m for m in METHODS if m not in ("approval", *SCORED, "quadratic", "sortition")),
    "marked": MARKED, "approval": ("approval",), "scored": SCORED,
    "quadratic": ("quadratic",), "none": ("sortition",),
}
MULTI_FAMILY_METHODS = {
    "ranked": tuple(m for m in MULTI_METHODS if m not in (*MULTI_APPROVAL, "reweighted-range", "cumulative", "sortition")),
    "marked": ("single-non-transferable",), "approval": MULTI_APPROVAL,
    "scored": ("reweighted-range",), "cumulative": ("cumulative",), "none": ("sortition",),
}


def _family(request, family, catalogs, engine, error):
    if not isinstance(family, str) or family not in catalogs:
        raise error("Unknown ballot family")
    if not isinstance(request, dict):
        raise error("Request must be an object")
    if request.get("method") not in catalogs[family]:
        raise error("Method is not compatible with " + family + " ballots")
    ballots = request.get("ballots")
    if isinstance(ballots, list):
        field = FIELDS[family]
        for ballot in ballots:
            if not isinstance(ballot, dict) or field is None or set(ballot) & set(FIELDS.values()) != {field}:
                raise error("Expected only " + family + " ballots")
    return engine(request)


def _dispatch(request, family, catalogs, engine, error, handlers):
    if family is not None:
        if not isinstance(family, str) or family not in handlers:
            raise error("Unknown ballot family")
        return handlers[family](request)
    # Infer a homogeneous input family, not an exclusive method classification.
    if isinstance(request, dict) and isinstance(request.get("ballots"), list):
        ballots = request["ballots"]
        if not ballots and request.get("method") == "sortition":
            return handlers["none"](request)
        formats = set()
        for ballot in ballots:
            if not isinstance(ballot, dict):
                return engine(request)
            formats.update(set(ballot) & set(FIELDS.values()))
        if len(formats) == 1:
            field = next(iter(formats))
            inferred = next((f for f in catalogs if FIELDS[f] == field), None)
            if inferred is not None:
                return handlers[inferred](request)
    return engine(request)


def simulate_request(request, family=None):
    return _dispatch(request, family, FAMILY_METHODS, simulate, ElectionError, {
        "ranked": simulate_ranked, "marked": simulate_marked, "approval": simulate_approval,
        "scored": simulate_scored, "quadratic": simulate_quadratic, "none": simulate_none})


def simulate_multi_request(request, family=None):
    return _dispatch(request, family, MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError, {
        "ranked": simulate_multi_ranked, "marked": simulate_multi_marked, "approval": simulate_multi_approval,
        "scored": simulate_multi_scored, "cumulative": simulate_multi_cumulative, "none": simulate_multi_none})


def simulate_ranked(request):
    return _family(request, "ranked", FAMILY_METHODS, simulate, ElectionError)


def simulate_marked(request):
    return _family(request, "marked", FAMILY_METHODS, simulate, ElectionError)


def simulate_approval(request):
    return _family(request, "approval", FAMILY_METHODS, simulate, ElectionError)


def simulate_scored(request):
    return _family(request, "scored", FAMILY_METHODS, simulate, ElectionError)


def simulate_quadratic(request):
    return _family(request, "quadratic", FAMILY_METHODS, simulate, ElectionError)


def simulate_none(request):
    return _family(request, "none", FAMILY_METHODS, simulate, ElectionError)


def simulate_multi_ranked(request):
    return _family(request, "ranked", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)


def simulate_multi_marked(request):
    return _family(request, "marked", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)


def simulate_multi_approval(request):
    return _family(request, "approval", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)


def simulate_multi_scored(request):
    return _family(request, "scored", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)


def simulate_multi_cumulative(request):
    return _family(request, "cumulative", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)


def simulate_multi_none(request):
    return _family(request, "none", MULTI_FAMILY_METHODS, simulate_multi, MultiElectionError)
