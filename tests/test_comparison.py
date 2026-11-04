"""Comparison catalog/renderer checks. No browser or extra packages required."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from comparison import catalog_data, install_comparison, render_comparison


class Matrix(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.rows = []
        self.statuses = []
        self.scripts = []
        self.payload = ""
        self.in_payload = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr" and "data-method" in attrs:
            self.rows.append(attrs["data-method"])
        if "data-status" in attrs:
            self.statuses.append(attrs["data-status"])
        if tag == "script":
            self.scripts.append(attrs)
            self.in_payload = attrs.get("id") == "comparison-data"

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_payload = False

    def handle_data(self, data):
        if self.in_payload:
            self.payload += data


class ComparisonTests(unittest.TestCase):
    def test_complete_static_tables_and_identical_embedded_catalogs(self):
        data = catalog_data()
        page = Matrix(render_comparison(data))
        self.assertEqual(json.loads(page.payload), data)
        methods = [m for catalog in data.values() for m in catalog["methods"]]
        self.assertEqual(page.rows, [m["id"] for m in methods])
        self.assertEqual(len(methods), 44)
        self.assertEqual(len(page.statuses), 25 * 25 + 19 * 28)
        self.assertEqual(len(page.scripts), 1)
        self.assertEqual(page.scripts[0]["type"], "application/json")

    def test_text_and_json_cannot_create_html_or_executable_scripts(self):
        data = copy.deepcopy(catalog_data())
        attack = '</script><script>alert("x")</script><img src=x onerror=alert(1)> &'
        method = data["single"]["methods"][0]
        for key in ("name", "summary", "variant", "tieNotes", "complexity", "limits", "ballot", "family"):
            method[key] = attack
        method["criteria"]["monotonicity"]["explanation"] = attack
        rendered = render_comparison(data)
        self.assertNotIn(attack, rendered)
        self.assertIn("&lt;img", rendered)
        page = Matrix(rendered)
        self.assertEqual(len(page.scripts), 1)
        self.assertEqual(json.loads(page.payload), data)

    def test_build_accepts_docapella_whitespace_and_copies_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "_assets").mkdir()
            page = out / "comparison.html"
            page.write_text('<html><head></head><body><div\n id="voting-comparison"\n >\n</div></body></html>')
            install_comparison(out)
            rendered = page.read_text()
            self.assertIn('src="/_assets/comparison.mjs"', rendered)
            self.assertIn('href="/_assets/comparison.css"', rendered)
            self.assertEqual(len(Matrix(rendered).rows), 44)
            for asset in ("comparison.mjs", "comparison.css"):
                self.assertEqual((out / "_assets" / asset).read_bytes(), (ROOT / "web" / asset).read_bytes())

    def test_build_fails_closed_for_missing_or_duplicate_marker(self):
        for marker in ("", '<div id="voting-comparison"></div>' * 2):
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder)
                (out / "comparison.html").write_text(marker)
                with self.assertRaisesRegex(AssertionError, "marker"):
                    install_comparison(out)

    def test_unknown_assessments_fail_closed(self):
        import comparison
        original = comparison.json.loads

        def modified_loads(text):
            value = original(text)
            if isinstance(value, list) and value and "criteria" in value[0]:
                value[0]["criteria"][next(iter(value[0]["criteria"]))]["status"] = "maybe"
            return value

        with patch.object(comparison.json, "loads", side_effect=modified_loads):
            with self.assertRaises(AssertionError):
                catalog_data()


if __name__ == "__main__":
    unittest.main()
