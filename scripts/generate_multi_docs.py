"""Generate multi-winner chapters and standalone Python/TypeScript/Go programs."""
import ast
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from multi_winner import METHODS, simulate, validate
from multi_fixtures import METHOD_IDS, EXPECTED_WINNERS, EXAMPLE_EXPLANATIONS, example_request
from generate_docs import closure, md_cell
from generate_go_examples import go_examples


def prose(value):
    """Keep mathematical prose out of Docapella's HTML/expression grammar."""
    return "".join(part if part.startswith("`") else html.escape(part, quote=False).replace("{", "&#123;").replace("}", "&#125;")
                   for part in re.split(r"(`+[^`]*`+)", value))


def python_example(method, request):
    source = (ROOT / "python/multi_winner.py").read_text()
    tree = ast.parse(source)
    lines = source.splitlines()
    declarations = {node.name: "\n".join(lines[node.lineno-1:node.end_lineno]) for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    imports = "\n".join(ast.get_source_segment(source, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)))
    function = METHODS[method].__name__
    _, candidates, ballots, seats, options = validate(request)
    normalized = {"method": method, "candidates": candidates, "ballots": ballots, "seats": seats, "options": options}
    return ("# Python 3.9+. Save as example.py and run: python3 example.py\n"
            "# Complete count for valid input. The API performs full validation.\n"
            + imports + "\n\n" + closure(function, declarations) + "\n\n"
            + "election = " + repr(normalized) + "\n"
            + f'counted = {function}(election["candidates"], election["ballots"], election["seats"], election["options"])\n'
            + 'answer = {"method": election["method"], "seats": election["seats"], **counted}\n'
            + "print(json.dumps(answer, indent=2))\n")


def typescript_example(method, request):
    source = (ROOT / "typescript/multi_winner.ts").read_text()
    shared = source.split("// BEGIN shared", 1)[1].split("// END shared", 1)[0].strip()
    matches = list(re.finditer(r"^(?:export )?function\*?\s+(\w+)\b", source, re.M))
    declarations = {match[1]: source[match.start():matches[i+1].start() if i+1 < len(matches) else len(source)].strip() for i, match in enumerate(matches)}
    function = "count" + "".join(x.title() for x in method.split("-"))
    _, candidates, ballots, seats, options = validate(request)
    context = {"method": method, "candidates": candidates, "seats": seats, "ballots": ballots,
               **options, "total": sum(b["count"] for b in ballots)}
    return ("// Node 22.18+. Save as example.ts and run: node example.ts\n"
            "// Complete count for valid input. The API performs full validation.\n"
            + shared + "\n\n" + closure(function, declarations) + "\n\n"
            + "const election: Context = " + json.dumps(context, indent=2) + ";\n"
            + f"console.log(JSON.stringify({function}(election), null, 2));\n")


def chapter(method, criteria, request, answer, py, ts, go):
    ident, name = method["id"], method["name"]
    committee = " and ".join(answer["winners"])
    rows = []
    for criterion in criteria:
        claim = method["criteria"][criterion["id"]]
        source = f' [Source]({claim["source"]}).' if claim.get("source") else ""
        rows.append(f'| [{criterion["name"]}](/multi-criteria.md#{criterion["id"]}) | {claim["status"]} | {md_cell(prose(claim["explanation"]))}{source} |')
    steps = "\n".join(f"{i}. {prose(step)}" for i, step in enumerate(method["steps"], 1))
    sources = "\n".join(f'- [{s["title"]}]({s["url"]})' for s in method["sources"])
    repo = "https://github.com/bnm2f28k6s/electoral-systems/blob/main/"
    return f'''# {name}

{prose(method["summary"])}

**Ballot:** {method["ballot"]}. **API identifier:** `{ident}` at `/multi/simulate`.

## Counting rule

{steps}

**Implemented variant:** {prose(method["variant"])}

**Ties:** {prose(method["tieNotes"])} The returned committee always has exactly `seats` members. Here `tie` reports a tie resolved during selection; it does not mean that electing several people is itself a tie. See [committee inputs and ties](/multi-ballots.md).

## Worked example

There are four candidates and two seats. Ranked examples use six A > B > C > D ballots, three C > D > A > B ballots, and one D > C > B > A ballot. Approval, score, and cumulative inputs are supplied explicitly as shown below. Sortition uses no ballots.

```json
{json.dumps(request, indent=2)}
```

**The selected committee is {committee}.** {EXAMPLE_EXPLANATIONS[ident]}

The response shows the intermediate calculation. Exact fractions are used internally where the rule needs them; JSON displays their numerical values.

```json
{json.dumps(answer, indent=2)}
```

## Run the algorithm

Each block includes its helpers and sample data, with no project imports. Python needs version 3.9 or newer; TypeScript runs directly with Node 22.18 or newer; Go needs 1.23 or newer. The [complete engines and HTTP server](/multi-api.md) validate inputs and enforce the documented computation limits. The server runs Python; the Go examples count locally without a server.

<CodeSelect title="{name.replace('&', '&amp;').replace(chr(34), '&quot;')} — complete algorithm">

```python
{py.rstrip()}
```

```typescript
{ts.rstrip()}
```

```go
{go.rstrip()}
```

</CodeSelect>

Download the standalone [Python]({repo}examples/multi/python/{ident}.py), [TypeScript]({repo}examples/multi/typescript/{ident}.ts), or [Go]({repo}examples/multi/go/{ident}.go) program.

## Simulate this committee through HTTP

Start `python3 python/server.py` from the repository root. Save the request above as `committee.json`, then run:

```sh
curl --fail-with-body http://127.0.0.1:8000/multi/simulate \\
  -H 'Content-Type: application/json' \\
  --data-binary @committee.json
```

The server executes this Python counting function and returns the response shown above. The [committee API guide](/multi-api.md) explains the response fields and errors. The [single-winner endpoint](/api-design.md) remains available separately.

## Criteria and assumptions

Read the [multi-winner criteria guide](/multi-criteria.md) before comparing labels. A criterion concerns whole classes of elections, not just this worked count. **Conditional** requires the stated domain or tie assumptions. **Unverified** records an unresolved assessment for the exact variant, rather than filling an empty source cell with a guarantee. Several committee criteria depend on how a voter compares groups of candidates; those assumptions are part of the definition.

| Criterion | Assessment | Explanation and source |
| --- | --- | --- |
{chr(10).join(rows)}

## Cost and limits

{prose(method["complexity"])}

{prose(method["limits"])} See the [enforced API bounds](/multi-api.md#limits). An exact enumeration's small input cap does not change its general computational complexity.

## Sources

{sources}

[Multi-winner catalog](/multi-methods.md) · [Ballots and committees](/multi-ballots.md) · [Criteria](/multi-criteria.md) · [Source notes](/multi-sources.md)
'''


def main():
    methods = json.loads((ROOT / "data/multi_methods.json").read_text())
    criteria = json.loads((ROOT / "data/multi_criteria.json").read_text())
    assert [m["id"] for m in methods] == METHOD_IDS
    go_programs = go_examples({m["id"]: example_request(m["id"]) for m in methods}, "multi")
    for folder in ("site/multi-methods", "examples/multi/python", "examples/multi/typescript", "examples/multi/go", "examples/multi/requests", "examples/multi/responses"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    for method in methods:
        ident = method["id"]
        assert set(method["criteria"]) == {criterion["id"] for criterion in criteria}, ident
        request = example_request(ident)
        answer = simulate(request)
        assert answer["winners"] == EXPECTED_WINNERS[ident], (ident, answer)
        py, ts = python_example(ident, request), typescript_example(ident, request)
        (ROOT / f"examples/multi/python/{ident}.py").write_text(py)
        (ROOT / f"examples/multi/typescript/{ident}.ts").write_text(ts)
        (ROOT / f"examples/multi/go/{ident}.go").write_text(go_programs[ident])
        for kind, data in (("requests", request), ("responses", answer)):
            (ROOT / f"examples/multi/{kind}/{ident}.json").write_text(json.dumps(data, indent=2) + "\n")
        (ROOT / f"site/multi-methods/{ident}.md").write_text(chapter(method, criteria, request, answer, py, ts, go_programs[ident]))
    catalog = "# Multi-winner method catalog\n\nA committee has a fixed number of seats. Some rules select the highest individual totals; others try to represent groups with different preferences. Electing several candidates does not automatically make a rule proportional.\n\nThis catalog covers all 19 rows in the [starting comparison's multi-winner table](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems#Criterion_tables), with precise counting variants, executable Python, TypeScript, and Go, and API requests. The [criteria guide](/multi-criteria.md) explains every comparison criterion, distinctions between committee preferences, and the additional approval-representation criteria used here.\n\n| Method | Ballot | Basic idea |\n| --- | --- | --- |\n"
    catalog += "\n".join(f'| [{m["name"]}](/multi-methods/{m["id"]}.md) | {md_cell(m["ballot"])} | {md_cell(prose(m["summary"]))} |' for m in methods)
    catalog += "\n\nStart with [bloc voting](/multi-methods/bloc.md) and [single non-transferable vote](/multi-methods/single-non-transferable.md), then compare [STV](/multi-methods/stv.md) and [proportional approval](/multi-methods/proportional-approval.md). Read the [ballot guide](/multi-ballots.md) before running a count, or return to the [single-winner catalog](/methods.md).\n"
    (ROOT / "site/multi-methods.md").write_text(catalog)
    nav = (ROOT / "site/navigation.yaml").read_text().split("- heading: Multiple winners\n")[0]
    api_nav = "- heading: API reference\n  items:\n    - open_api_spec: openapi.json\n"
    nav = nav.replace(api_nav, "")
    nav += "- heading: Multiple winners\n  items:\n"
    for label, href in (("Method catalog", "multi-methods"), ("Ballots and committees", "multi-ballots"), ("Committee criteria", "multi-criteria"), ("Committee sources", "multi-sources"), ("Committee simulation API", "multi-api")):
        nav += f"    - label: {label}\n      href: /{href}.md\n"
    for m in methods:
        nav += f'    - label: {json.dumps(m["name"])}\n      href: /multi-methods/{m["id"]}.md\n'
    (ROOT / "site/navigation.yaml").write_text(nav + api_nav)
    print(f"Generated {len(methods)} multi-winner chapters and {3*len(methods)} standalone programs")


if __name__ == "__main__":
    main()
