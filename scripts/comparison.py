"""Progressively enhanced comparison, generated from the existing catalogs.

Docapella owns the page shell. The production build fills one explicit marker
and copies two site-local assets; no upstream templates or CDN packages change.
"""
import html
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MARKER = r'<div\s+id="voting-comparison"\s*>\s*</div>'
STATUSES = {
    "pass": "Pass", "fail": "Fail", "conditional": "Conditional",
    "unverified": "Unverified", "not-applicable": "Not applicable",
}
SCOPES = {"single": ("Single-winner", "methods", "criteria"),
          "multi": ("Committee", "multi_methods", "multi_criteria")}


def escape(value):
    return html.escape(str(value), quote=True)


def catalog_data():
    data = {}
    for scope, (label, methods_file, criteria_file) in SCOPES.items():
        methods = json.loads((ROOT / f"data/{methods_file}.json").read_text())
        criteria = json.loads((ROOT / f"data/{criteria_file}.json").read_text())
        ids = {c["id"] for c in criteria}
        assert len(ids) == len(criteria), "Duplicate criterion"
        assert len({m["id"] for m in methods}) == len(methods), "Duplicate method"
        for method in methods:
            assert set(method["criteria"]) == ids, method["id"]
            assert all(c["status"] in STATUSES for c in method["criteria"].values())
        data[scope] = {"label": label, "methods": methods, "criteria": criteria}
    return data


def table(scope, catalog):
    folder = "methods" if scope == "single" else "multi-methods"
    definitions = "criteria" if scope == "single" else "multi-criteria"
    headers = '<th scope="col">Method</th><th scope="col">Family</th><th scope="col">Ballot</th>'
    for criterion in catalog["criteria"]:
        ident = escape(criterion["id"])
        headers += (f'<th scope="col" data-criterion="{ident}"><a href="/{definitions}.html#{ident}" '
                    f'title="{escape(criterion["definition"])}">{escape(criterion["name"])}</a></th>')
    rows = []
    for method in catalog["methods"]:
        ident = escape(method["id"])
        details = ''.join(f'<dt>{label}</dt><dd>{escape(method[key])}</dd>' for label, key in (
            ("Variant", "variant"), ("Ties", "tieNotes"), ("Counting cost", "complexity"), ("Limits", "limits")))
        cells = (f'<th scope="row"><a href="/{folder}/{ident}.html">{escape(method["name"])}</a>'
                 f'<p>{escape(method["summary"])}</p><details><summary>Rule and counting details</summary>'
                 f'<dl>{details}</dl></details></th><td>{escape(method["family"])}</td>'
                 f'<td>{escape(method["ballot"])}</td>')
        for criterion in catalog["criteria"]:
            cid = escape(criterion["id"])
            claim = method["criteria"][criterion["id"]]
            status = claim["status"]
            source = f'<p><a href="{escape(claim["source"])}">Assessment source</a></p>' if claim.get("source") else ''
            cells += (f'<td data-criterion="{cid}" data-status="{status}"><details>'
                      f'<summary><span class="comparison-status status-{status}">{STATUSES[status]}</span>'
                      f'<span class="comparison-sr">: {escape(method["name"])}, {escape(criterion["name"])}</span></summary>'
                      f'<p>{escape(claim["explanation"])}</p>{source}</details></td>')
        rows.append(f'<tr data-method="{ident}">{cells}</tr>')
    return (f'<section data-scope="{scope}" aria-label="{catalog["label"]} comparison">'
            f'<h2>{catalog["label"]} comparison</h2>'
            '<div class="comparison-scroll" tabindex="0" role="region" '
            f'aria-label="Scrollable {catalog["label"].lower()} matrix">'
            f'<table><caption>{catalog["label"]} methods and qualified criterion assessments</caption>'
            f'<thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')


def render_comparison(data):
    # Escape HTML delimiters inside the inert JSON script, including </script>.
    payload = json.dumps(data, ensure_ascii=True).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return ('<div id="voting-comparison">'
            '<div id="comparison-controls" hidden></div>'
            '<p id="comparison-count" role="status" aria-live="polite" aria-atomic="true"></p>'
            '<p id="comparison-empty" hidden>No methods match all filters. Change a requirement or reset the comparison.</p>'
            + ''.join(table(scope, catalog) for scope, catalog in data.items())
            + '<noscript><p>JavaScript is off. Both complete comparison tables are shown above.</p></noscript>'
            + f'<script type="application/json" id="comparison-data">{payload}</script></div>')


def install_comparison(out):
    page = out / "comparison.html"
    text = page.read_text()
    assert len(re.findall(MARKER, text)) == 1, "Docapella comparison marker missing or duplicated"
    text = re.sub(MARKER, lambda match: render_comparison(catalog_data()), text)
    text = text.replace('</head>', '<link rel="stylesheet" href="/_assets/comparison.css"></head>')
    text = text.replace('</body>', '<script type="module" src="/_assets/comparison.mjs"></script></body>')
    page.write_text(text)
    for name in ("comparison.css", "comparison.mjs"):
        shutil.copyfile(ROOT / "web" / name, out / "_assets" / name)
