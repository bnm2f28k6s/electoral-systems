"""Complete static worked examples plus an optional local browser simulator."""
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MARKER = r'<div\s+id="simulator-root"\s*>\s*</div>'


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def simulator_data():
    data = {}
    for scope, fixture, engine, catalog in (
        ('single', 'fixtures', 'electoral', 'methods'),
        ('multi', 'multi_fixtures', 'multi_winner', 'multi_methods'),
    ):
        samples = load(ROOT / f'scripts/{fixture}.py')
        implementation = load(ROOT / f'python/{engine}.py')
        methods = json.loads((ROOT / f'data/{catalog}.json').read_text())
        assert {m['id'] for m in methods} == set(samples.METHOD_IDS)
        data[scope] = {'label': 'Single-winner' if scope == 'single' else 'Committee', 'methods': []}
        for method in methods:
            request = samples.example_request(method['id'])
            result = implementation.simulate(request)
            assert result['winners'] == samples.EXPECTED_WINNERS[method['id']]
            data[scope]['methods'].append({**{k: method[k] for k in ('id', 'name', 'family', 'ballot', 'summary', 'variant', 'tieNotes', 'complexity', 'limits')}, 'request': request, 'result': result})
    return data


def render_simulator(data):
    esc = lambda value: html.escape(str(value), quote=True)
    pretty = lambda value: esc(json.dumps(value, indent=2, ensure_ascii=False))
    sections = []
    for scope, domain in data.items():
        folder = 'methods' if scope == 'single' else 'multi-methods'
        examples = []
        for method in domain['methods']:
            notes = ''.join(f'<dt>{esc(key)}</dt><dd>{esc(method[key])}</dd>' for key in ('family', 'ballot', 'variant', 'tieNotes', 'complexity', 'limits'))
            examples.append(f'<details data-example="{scope}/{esc(method["id"])}"><summary>{esc(method["name"])}</summary><p>{esc(method["summary"])}</p><dl>{notes}</dl><p><a href="/{folder}/{esc(method["id"])}.html">Method chapter</a></p><h4>Request</h4><pre>{pretty(method["request"])}</pre><h4>Result</h4><pre>{pretty(method["result"])}</pre></details>')
        sections.append(f'<section><h2>{esc(domain["label"])} worked examples</h2>{"".join(examples)}</section>')
    payload = json.dumps(data, ensure_ascii=True).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return ('<div id="simulator-root"><p>These complete worked requests and results are available without JavaScript. Optional interactive counting runs locally in your browser using the existing TypeScript engine compiled to JavaScript. No server, installation, or manual download is needed; simulation requests are not sent over the network. Loading this documentation and its assets still uses the network.</p>'
            '<p><a href="/api-design.html">Single-winner API</a> · <a href="/multi-api.html">Committee API</a> · <a href="https://github.com/bnm2f28k6s/electoral-systems/tree/main/examples">Download standalone examples</a></p>'
            '<p id="simulator-status" role="status" aria-live="polite" aria-atomic="true">Static examples are ready. Interactive counting is optional.</p><div id="simulator-controls" hidden></div>'
            + ''.join(sections) + f'<script id="simulator-data" type="application/json">{payload}</script></div>')


def install_simulator(out):
    out = Path(out)
    page = out / 'simulator.html'
    text = page.read_text()
    assert len(re.findall(MARKER, text)) == 1, 'Docapella simulator marker missing or duplicated'
    text = re.sub(MARKER, lambda _: render_simulator(simulator_data()), text)
    text = text.replace('</head>', '<link rel="stylesheet" href="/_assets/simulator.css"></head>')
    text = text.replace('</body>', '<script type="module" src="/_assets/simulator.mjs"></script></body>')
    page.write_text(text)
    (out / '_assets').mkdir(exist_ok=True)
    for name in ('simulator.css', 'simulator.mjs', 'simulator-worker.mjs'):
        shutil.copyfile(ROOT / 'web' / name, out / '_assets' / name)
