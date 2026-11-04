"""Build method chapters and standalone examples from the tested source files.

Python dependency closures use its AST; TypeScript uses top-level function
declarations (the engine deliberately keeps shared declarations in one block).
Generated snippets have no project imports and include their own sample input.
"""
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from electoral import METHODS, simulate, validate
from fixtures import METHOD_IDS, EXPECTED_WINNERS, example_request


def dependency_names(source, names):
    return {name for name in names if re.search(r"\b" + re.escape(name) + r"\b", source)}


def closure(start, declarations):
    needed, pending = set(), [start]
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        needed.add(name)
        pending.extend(dependency_names(declarations[name], declarations) - needed)
    return "\n\n".join(source.rstrip() for name, source in declarations.items() if name in needed)


def python_example(method, request):
    source = (ROOT / "python/electoral.py").read_text()
    tree = ast.parse(source)
    lines = source.splitlines()
    declarations = {node.name: "\n".join(lines[node.lineno - 1:node.end_lineno]) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    imports = "\n".join(ast.get_source_segment(source, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)))
    function = METHODS[method].__name__
    # A chapter demonstrates the algorithm on valid data; server-side validation
    # is separately documented, tested, and retained in the complete engine.
    _, candidates, ballots, options = validate(request)
    normalized = {"method": method, "candidates": candidates, "ballots": ballots, "options": options}
    return ("# Python 3.9+. Save as example.py and run: python3 example.py\n"
            "# Self-contained count for valid input; the API also validates requests.\n"
            + imports + "\n\n" + closure(function, declarations) + "\n\n"
            + "election = " + repr(normalized) + "\n"
            + f'counted = {function}(election["candidates"], election["ballots"], election["options"])\n'
            + 'answer = {"method": election["method"], **counted, "tie": len(counted["winners"]) > 1}\n'
            + 'print(json.dumps(answer, indent=2))\n')


def typescript_example(method, request):
    source = (ROOT / "typescript/electoral.ts").read_text()
    shared = source.split("// BEGIN shared", 1)[1].split("// END shared", 1)[0].strip()
    matches = list(re.finditer(r"^(?:export )?function\*?\s+(\w+)\b", source, re.M))
    declarations = {match[1]: source[match.start():matches[i + 1].start() if i + 1 < len(matches) else len(source)].strip() for i, match in enumerate(matches)}
    function = "count" + "".join(x.title() for x in method.split("-"))
    body = closure(function, declarations)
    _, candidates, ballots, options = validate(request)
    context = {"method": method, "candidates": candidates, "ballots": ballots,
               **options, "total": sum(b["count"] for b in ballots)}
    return ("// Node 22.18+ (native TypeScript). Save as example.ts; run: node example.ts\n"
            "// Self-contained count for valid input; the API also validates requests.\n"
            + shared + "\n\n" + body + "\n\n"
            + "const election: Context = " + json.dumps(context, indent=2) + ";\n"
            + f"console.log(JSON.stringify({function}(election), null, 2));\n")


def md_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def chapter(method, criteria, request, answer, py, ts):
    name, ident = method["name"], method["id"]
    winners = ", ".join(answer["winners"])
    result_text = (f"The sampled winner is **{winners}** with seed 1. The distribution in the response describes the rule; the sampled name is one reproducible draw."
                   if "lottery" in answer else f"The result is **{winners}**" + (" (a final tie)." if answer["tie"] else "."))
    ballot_text = "There are no ballots: the candidates are A, B, and C." if ident == "sortition" else (
        "This smaller profile has three A > B > C ballots, two B > C > A ballots, and two C > B > A ballots. B already beats both rivals, so no swaps are needed. Seven voters fit the exact search limit."
        if ident == "dodgson" else
        "Use the [nine-voter profile](/ballots.md#the-nine-voter-example) below. The `count` field groups identical ballots. Approval, grade, and credit values are explicitly supplied rather than inferred from rankings.")
    rows = []
    for criterion in criteria:
        claim = method["criteria"][criterion["id"]]
        source = claim.get("source")
        evidence = f" [Source]({source})." if source else ""
        rows.append(f'| [{criterion["name"]}](/criteria.md#{criterion["id"]}) | {claim["status"]} | {md_cell(claim["explanation"])}{evidence} |')
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(method["steps"], 1))
    sources = "\n".join(f'- [{item["title"]}]({item["url"]})' for item in method["sources"])
    repo = "https://github.com/bnm2f28k6s/electoral-systems/blob/codex/initial-single-winner-examples/"
    return f'''# {name}

{method["summary"]}

**Ballot:** {method["ballot"]}. **API identifier:** `{ident}`.

## Counting rule

{steps}

**Variant used here:** {method["variant"]}

**Ties:** {method["tieNotes"]} See [shared tie handling](/ballots.md#ties) for how candidate priority affects internal decisions.

## Worked example

{ballot_text}

```json
{json.dumps(request, indent=2)}
```

{result_text} The trace records intermediate totals, eliminations, comparisons, or the lottery used by this rule.

```json
{json.dumps(answer, indent=2)}
```

## Run the algorithm

Each block is a complete program with its sample input and required helpers. Python requires 3.9 or newer; TypeScript runs directly with Node 22.18 or newer. Replace the sample with valid input using the same format. The examples focus on counting valid data; the [API server](/api-design.md) performs full validation before running the count.

<CodeSelect title="{name.replace('&', '&amp;').replace(chr(34), '&quot;')} — complete algorithm">

```python
{py.rstrip()}
```

```typescript
{ts.rstrip()}
```

</CodeSelect>

Download the standalone [Python]({repo}examples/python/{ident}.py) or [TypeScript]({repo}examples/typescript/{ident}.ts) file. The complete engines use the same functions.

## Simulate this method through HTTP

Start the server from the repository with `python3 python/server.py`. Save the request above as `election.json`, then run:

```sh
curl --fail-with-body http://127.0.0.1:8000/simulate \\
  -H 'Content-Type: application/json' \\
  --data-binary @election.json
```

The server runs the Python algorithm and returns the JSON shown above. GitHub Pages itself does not execute API requests. See the [request and error reference](/api-design.md).

## Criteria and assumptions

These are properties of rules over whole classes of elections, not conclusions proved by the worked example. **Pass** and **fail** refer to the stated mathematical interpretation; **conditional** requires the stated assumptions; **unverified** means this guide has not established a result; **not-applicable** means the criterion is not defined for this input or outcome model. A fixed priority can change properties at exact ties. See the [definitions and interpretation guide](/criteria.md) before comparing rows.

| Criterion | Assessment | Explanation and evidence |
| --- | --- | --- |
{chr(10).join(rows)}

## Cost and limits

{method["complexity"]}

{method["limits"]} The [API guide](/api-design.md) lists enforced bounds. Complexity describes the teaching implementation, not a guarantee about every algorithm for the same rule.

## Sources

{sources}

[All methods](/methods.md) · [Ballot formats](/ballots.md) · [Criteria](/criteria.md)
'''


def main():
    methods = json.loads((ROOT / "data/methods.json").read_text())
    criteria = json.loads((ROOT / "data/criteria.json").read_text())
    assert [m["id"] for m in methods] == METHOD_IDS
    for folder in ("site/methods", "examples/python", "examples/typescript", "examples/requests", "examples/responses"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    for method in methods:
        ident = method["id"]
        request = example_request(ident)
        answer = simulate(request)
        assert answer["winners"] == EXPECTED_WINNERS[ident], (ident, answer)
        assert set(method["criteria"]) == {c["id"] for c in criteria}, ident
        py, ts = python_example(ident, request), typescript_example(ident, request)
        (ROOT / f"examples/python/{ident}.py").write_text(py)
        (ROOT / f"examples/typescript/{ident}.ts").write_text(ts)
        for kind, value in (("requests", request), ("responses", answer)):
            (ROOT / f"examples/{kind}/{ident}.json").write_text(json.dumps(value, indent=2) + "\n")
        (ROOT / f"site/methods/{ident}.md").write_text(chapter(method, criteria, request, answer, py, ts))
    catalog = "# Single-winner method catalog\n\nChoose a rule by the information voters provide and the counting steps you want to understand. Every method below has a worked example, complete Python and TypeScript, all 25 criterion entries, and an executable API request.\n\nCoverage follows every method row in the [starting comparison](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Compliance_of_selected_single-winner_methods), including random selection and the specified quadratic demonstration. This is a coverage map, not a ranking of methods.\n\n| Method | Ballot | Basic idea |\n| --- | --- | --- |\n"
    catalog += "\n".join(f'| [{m["name"]}](/methods/{m["id"]}.md) | {md_cell(m["ballot"])} | {md_cell(m["summary"])} |' for m in methods)
    (ROOT / "site/methods.md").write_text(catalog + "\n\nRead [ballot formats](/ballots.md) and [criteria](/criteria.md) to understand the assumptions behind comparisons. [Sources](/sources.md) explain the research boundaries.\n")
    navigation = "- heading: Learn\n  items:\n"
    for label, href in (("Introduction", "/"), ("Method catalog", "/methods.md"), ("Ballots and ties", "/ballots.md"), ("Criteria", "/criteria.md"), ("Sources", "/sources.md"), ("Local simulation API", "/api-design.md")):
        navigation += f"    - label: {label}\n      href: {href}\n"
    for family in dict.fromkeys(m["family"] for m in methods):
        navigation += f"- heading: {json.dumps(family)}\n  items:\n"
        for m in methods:
            if m["family"] == family:
                navigation += f'    - label: {json.dumps(m["name"])}\n      href: /methods/{m["id"]}.md\n'
    navigation += "- heading: API reference\n  items:\n    - open_api_spec: openapi.json\n"
    (ROOT / "site/navigation.yaml").write_text(navigation)
    print(f"Generated {len(methods)} chapters, {2 * len(methods)} standalone programs, and matching API fixtures")
    from generate_multi_docs import main as generate_multi
    generate_multi()


if __name__ == "__main__":
    main()
