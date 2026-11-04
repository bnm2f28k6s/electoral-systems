"""Extend the shared OpenAPI document with implemented committee operations."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from multi_winner import simulate
from multi_fixtures import METHOD_IDS, APPROVAL_METHODS, example_request


def extend(spec):
    from generate_openapi import array, object_schema
    identifier = {"type": "string", "minLength": 1, "maxLength": 100}
    count = {"type": "integer", "minimum": 1, "maximum": 1000000, "default": 1}
    schemas = spec["components"]["schemas"]
    schemas["MultiOptions"] = object_schema({
        "maxScore": {"type": "integer", "minimum": 1, "maximum": 100, "default": 5},
        "budget": {"type": "integer", "minimum": 1, "maximum": 1000000, "default": 100},
        "limit": {"type": "integer", "minimum": 1, "maximum": 32, "description": "Limited-vote marks: default max(1, seats−1). Must be below seats, except the one-seat limit is one."},
        "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295, "default": 1},
    }, [])
    schemas["CumulativeBallot"] = object_schema({
        "votes": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0, "maximum": 1000000}, "description": "Explicit nonnegative allocation to every candidate; sum must not exceed budget."},
        "count": count,
    }, ["votes"])
    ranked = [m for m in METHOD_IDS if m not in APPROVAL_METHODS | {"reweighted-range", "cumulative", "sortition", "single-non-transferable"}]
    refs = []
    for title, methods, ballot in [
        ("MultiRankedElection", ranked, "RankedBallot"),
        ("MultiApprovalElection", [m for m in METHOD_IDS if m in APPROVAL_METHODS], "ApprovalBallot"),
        ("MultiScoredElection", ["reweighted-range"], "ScoreBallot"),
        ("MultiCumulativeElection", ["cumulative"], "CumulativeBallot"),
        ("MultiMarkedElection", ["single-non-transferable"], "MarkBallot"),
        ("MultiSortitionElection", ["sortition"], None),
    ]:
        item = {"$ref": "#/components/schemas/" + ballot} if ballot else {}
        if title == "MultiMarkedElection":
            item = {"oneOf": [{"$ref": "#/components/schemas/RankedBallot"}, {"$ref": "#/components/schemas/MarkBallot"}]}
        schemas[title] = object_schema({
            "method": {"type": "string", "enum": methods},
            "candidates": array(identifier, minItems=1, maxItems=32, uniqueItems=True),
            "seats": {"type": "integer", "minimum": 1, "maximum": 32, "description": "Number of distinct candidates to elect; cannot exceed candidate count."},
            "ballots": array(item, minItems=1, maxItems=10000) if ballot else array({}, maxItems=0),
            "options": {"$ref": "#/components/schemas/MultiOptions"},
        }, ["method", "candidates", "seats", "ballots"])
        refs.append({"$ref": "#/components/schemas/" + title})
    schemas["MultiElection"] = {"oneOf": refs, "description": "Committee count with a required seat count. Ballot formats, sum budgets, dynamic limits, and exact-search caps are checked by the server. Rankings must be complete and strict. The single-winner request model is separate."}
    schemas["MultiResult"] = {
        "type": "object", "required": ["method", "seats", "winners", "tie", "trace"],
        "properties": {
            "method": {"type": "string", "enum": METHOD_IDS},
            "seats": {"type": "integer", "minimum": 1},
            "winners": array(identifier, minItems=1, maxItems=32, uniqueItems=True, description="Exactly seats selected members, listed in original candidate order."),
            "tie": {"type": "boolean", "description": "True when selection used a tie resolution. Multiple elected members do not themselves mean a tied result."},
            "trace": array({"type": "object", "additionalProperties": True}, description="Method-specific tally, transfer, load, coalition, committee-comparison, or seeded draw information."),
        },
    }
    catalog = json.loads((ROOT / "data/multi_methods.json").read_text())
    spec["info"]["version"] = "1.1.0"
    spec["info"]["description"] += " Committee methods use /multi/systems and /multi/simulate with an explicit seats field. Their winners form one selected committee, and their tie flag records selection ties. The original single-winner endpoints retain their existing response meaning."
    spec["tags"].append({"name": "Committees", "description": "Discover and execute multi-winner rules. See the committee API guide for variants, exact-search limits, and tie semantics."})
    spec["paths"]["/multi/systems"] = {"get": {
        "tags": ["Committees"], "operationId": "listCommitteeSystems", "summary": "List 19 implemented multi-winner methods",
        "responses": {"200": {"description": "Committee counting method identifiers.", "content": {"application/json": {
            "schema": object_schema({"methods": array({"type": "string", "enum": METHOD_IDS})}, ["methods"]),
            "example": {"methods": METHOD_IDS},
        }}}},
    }}
    responses = {key: value for key, value in spec["paths"]["/simulate"]["post"]["responses"].items() if key != "200"}
    responses["200"] = {"description": "One selected committee with exactly seats distinct members and an executed count trace.", "content": {"application/json": {
        "schema": {"$ref": "#/components/schemas/MultiResult"},
        "examples": {method: {"value": simulate(example_request(method))} for method in METHOD_IDS},
    }}}
    spec["paths"]["/multi/simulate"] = {"post": {
        "tags": ["Committees"], "operationId": "simulateCommittee", "summary": "Elect a committee using the named rule",
        "description": "Runs the Python multi-winner engine. Candidate order supplies deterministic priority for selection ties; final winners are returned in input order. Random draws advance the seeded generator once per seat. Count is the multiplicity of identical voters. Integer Droop STV and CPO-STV, exact-quota QBS/EAR, sequential Phragmen, and both Simpson extensions are specified in their chapters.",
        "requestBody": {"required": True, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/MultiElection"},
            "examples": {method: {"summary": next(m["name"] for m in catalog if m["id"] == method), "value": example_request(method)} for method in METHOD_IDS},
        }}},
        "responses": responses,
    }}
    return spec
