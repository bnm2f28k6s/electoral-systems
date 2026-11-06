import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from simulator import simulator_data, render_simulator, install_simulator


class SimulatorTests(unittest.TestCase):
    def test_complete_static_examples(self):
        data = simulator_data()
        output = render_simulator(data)
        self.assertEqual(sum(len(d['methods']) for d in data.values()), 44)
        self.assertEqual(output.count('data-example='), 44)
        embedded = re.search(r'id="simulator-data" type="application/json">(.*?)</script>', output).group(1)
        self.assertEqual(json.loads(embedded), data)
        self.assertIn('id="simulator-controls" hidden', output)
        for domain in data.values():
            for method in domain['methods']:
                self.assertIn('trace', method['result'])

    def test_inert_json_and_html(self):
        data = simulator_data()
        data['single']['methods'][0]['name'] = '</script><img src=x onerror=alert(1)>'
        output = render_simulator(data)
        self.assertNotIn('<img', output)
        self.assertIn('\\u003c/script\\u003e', output)

    def test_install_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            page = out / 'simulator.html'
            for marker in ('', '<div id="simulator-root"></div>' * 2):
                page.write_text(marker)
                with self.assertRaises(AssertionError):
                    install_simulator(out)
            page.write_text('<head></head><body><div id="simulator-root">\n </div></body>')
            install_simulator(out)
            self.assertIn('/_assets/simulator.mjs', page.read_text())
            for name in ('simulator.mjs', 'simulator-worker.mjs', 'simulator.css'):
                self.assertEqual((out / '_assets' / name).read_bytes(), (ROOT / 'web' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
