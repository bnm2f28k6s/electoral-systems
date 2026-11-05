"""Generate the API contract and executed examples from the shared catalog."""
import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from electoral import simulate
from fixtures import METHOD_IDS, example_request


def array(items, **kw):
    return {"type": "array", "items": items, **kw}


def object_schema(properties, required, **kw):
    return {"type": "object", "properties": properties, **({"required": required} if required else {}),
            "additionalProperties": False, **kw}


def add_family_paths(spec, prefix, catalogs, union, result):
    """Narrow existing method-specific unions to one input format per route."""
    schemas = spec["components"]["schemas"]
    ballot_names = {"ranked": "RankedBallot", "marked": "MarkBallot", "approval": "ApprovalBallot",
                    "scored": "ScoreBallot", "quadratic": "CreditBallot", "cumulative": "CumulativeBallot"}
    for family, methods in catalogs.items():
        refs = []
        for ref in schemas[union]["oneOf"]:
            source = ref["$ref"].split("/")[-1]
            schema = deepcopy(schemas[source])
            accepted = [m for m in schema["properties"]["method"]["enum"] if m in methods]
            if not accepted:
                continue
            schema["properties"]["method"]["enum"] = accepted
            if family != "none":
                schema["properties"]["ballots"]["items"] = {"$ref": "#/components/schemas/" + ballot_names[family]}
            name = source + family.title() + "Request"
            schemas[name] = schema
            refs.append({"$ref": "#/components/schemas/" + name})
        name = union + family.title() + "Request"
        schemas[name] = {"oneOf": refs}
        operation = deepcopy(spec["paths"][prefix]["post"])
        operation["operationId"] += family.title()
        operation["summary"] = "Count " + family + " ballots"
        operation["description"] = "Accepts only the named ballot format, without coercion or mixed formats. Method compatibility is checked even for an empty ballot array. All canonical engine validation and limits apply."
        content = operation["requestBody"]["content"]["application/json"]
        content["schema"] = {"$ref": "#/components/schemas/" + name}
        # Facade examples may use ranking for a method that also accepts choice.
        examples = {}
        for method, example in content.get("examples", {}).items():
            if method not in methods:
                continue
            value = example["value"]
            if family == "ranked" and value["ballots"] and "choice" in value["ballots"][0]:
                for b in value["ballots"]:
                    choice = b.pop("choice")
                    b["ranking"] = [choice] + [c for c in value["candidates"] if c != choice]
            if family == "marked":
                for b in value["ballots"]:
                    if "ranking" in b:
                        ranking = b.pop("ranking")
                        b["choice"] = ranking[-1] if method == "anti-plurality" else ranking[0]
            expected = {"ranked": "ranking", "marked": "choice", "approval": "approvals", "scored": "scores", "quadratic": "credits", "cumulative": "votes"}.get(family)
            if family == "none" or all(expected in b for b in value["ballots"]):
                examples[method] = example
        content["examples"] = examples
        operation["responses"]["200"]["content"]["application/json"] = {
            "schema": {"$ref": "#/components/schemas/" + result}}
        spec["paths"][prefix + "/" + family] = {"post": operation}


def main():
    string = {"type": "string", "minLength": 1, "maxLength": 100}
    count = {"type": "integer", "minimum": 1, "maximum": 1000000, "default": 1}
    schemas = {
        "Options": object_schema({
            "maxScore": {"type": "integer", "minimum": 1, "default": 5},
            "budget": {"type": "integer", "minimum": 1, "default": 100},
            "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295, "default": 1},
        }, []),
        "RankedBallot": object_schema({"ranking": array(string, minItems=1, uniqueItems=True), "count": count}, ["ranking"]),
        "MarkBallot": object_schema({"choice": string, "count": count}, ["choice"]),
        "ApprovalBallot": object_schema({"approvals": array(string, uniqueItems=True), "count": count}, ["approvals"]),
        "ScoreBallot": object_schema({"scores": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}}, "count": count}, ["scores"]),
        "CreditBallot": object_schema({"credits": {"type": "object", "additionalProperties": {"type": "integer", "minimum": -1000, "maximum": 1000}}, "count": count}, ["credits"]),
        "Error": {"type": "object", "required": ["error"], "properties": {"error": {"type": "string"}}},
        "Result": {"type": "object", "required": ["method", "winners", "tie", "trace"], "properties": {
            "method": {"type": "string", "enum": METHOD_IDS}, "winners": array(string, minItems=1),
            "tie": {"type": "boolean", "description": "True when the final result contains multiple co-winners."},
            "trace": array({"type": "object", "additionalProperties": True}),
            "lottery": array(object_schema({"candidate": string, "probability": {"type": "number", "minimum": 0, "maximum": 1}}, ["candidate", "probability"])),
        }},
    }
    rank_methods = [x for x in METHOD_IDS if x not in ("approval", "score", "star", "majority-judgment", "quadratic", "sortition", "plurality", "anti-plurality", "random-ballot")]
    request_refs = []
    for title, methods, ballot in [
        ("RankedElection", rank_methods, "RankedBallot"),
        ("MarkedElection", ["plurality", "anti-plurality", "random-ballot"], "MarkBallot"),
        ("ApprovalElection", ["approval"], "ApprovalBallot"),
        ("ScoredElection", ["score", "star", "majority-judgment"], "ScoreBallot"),
        ("QuadraticElection", ["quadratic"], "CreditBallot"),
        ("SortitionElection", ["sortition"], None),
    ]:
        ballot_schema = {"$ref": "#/components/schemas/" + ballot} if ballot else {}
        if title == "MarkedElection":
            ballot_schema = {"oneOf": [{"$ref": "#/components/schemas/MarkBallot"}, {"$ref": "#/components/schemas/RankedBallot"}]}
        ballots = array(ballot_schema, minItems=1, maxItems=10000) if ballot else array({}, maxItems=0)
        schemas[title] = object_schema({
            "method": {"type": "string", "enum": methods},
            "candidates": array(string, minItems=1, maxItems=32, uniqueItems=True), "ballots": ballots,
            "options": {"$ref": "#/components/schemas/Options"},
        }, ["method", "candidates", "ballots"])
        request_refs.append({"$ref": "#/components/schemas/" + title})
    schemas["Election"] = {"oneOf": request_refs, "description": "Use the ballot format accepted by the chosen method. Rankings must list every candidate exactly once. Score and credit maps must include every candidate. Additional numeric and computation limits are documented in the API guide and enforced by the server."}
    errors = {str(status): {"description": description, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}} for status, description in [(400, "Invalid JSON, method, ballot, option, or profile."), (408, "Request body timed out."), (413, "Request body or computation exceeds a published teaching limit."), (415, "Content-Type must be application/json.")]}
    catalog = json.loads((ROOT / "data/methods.json").read_text())
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Electoral systems simulation API", "version": "1.0.0", "description": "Local teaching server executing the same Python counting algorithms shown in the chapters. Start it with `python3 python/server.py`. GitHub Pages hosts documentation only. Single-winner results include intermediate counts; a final tie remains a set of co-winners. See the API guides for exact variants, tie priorities, and computational limits."},
        "servers": [{"url": "http://127.0.0.1:8000", "description": "Local Python simulation server"}],
        "tags": [{"name": "Systems", "description": "Available method identifiers."}, {"name": "Simulations", "description": "Execute a synthetic single-winner election."}],
        "paths": {
            "/systems": {"get": {"tags": ["Systems"], "operationId": "listSystems", "summary": "List implemented methods", "responses": {"200": {"description": "All 25 method identifiers.", "content": {"application/json": {"schema": object_schema({"methods": array({"type": "string", "enum": METHOD_IDS})}, ["methods"]), "example": {"methods": METHOD_IDS}}}}}}},
            "/simulate": {"post": {"tags": ["Simulations"], "operationId": "simulateElection", "summary": "Count ballots using a named method", "description": "Ballot counts repeat identical voters; they are not score multipliers selected by voters. Candidate array order is the fixed priority for internal ties. Complete rankings are required for ranked methods. Two-round uses a fixed-preference simulation, not a second voter survey. Seeded lotteries return both a sampled winner and its distribution.", "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Election"}, "examples": {m: {"summary": next(x["name"] for x in catalog if x["id"] == m), "value": example_request(m)} for m in METHOD_IDS}}}}, "responses": {
                "200": {"description": "Executed count, final co-winners or sampled winner, and method-specific trace.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Result"}, "examples": {m: {"value": simulate(example_request(m))} for m in METHOD_IDS}}}}, **errors}}},
        },
        "components": {"schemas": schemas},
    }
    from generate_multi_openapi import extend
    spec = extend(spec)
    from api import FAMILY_METHODS
    add_family_paths(spec, "/simulate", FAMILY_METHODS, "Election", "Result")
    (ROOT / "site/openapi.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
