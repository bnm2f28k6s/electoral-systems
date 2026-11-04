"""Verify published examples, standalone code, and the actual HTTP contract."""
import http.client
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python"), str(ROOT / "scripts")]
from electoral import simulate
from fixtures import METHOD_IDS, EXPECTED_WINNERS
from server import Handler


UNICODE_IDS = ["\ud800", "\udfff", "A\ud800B", "🌱"]


def assert_equivalent(test, actual, expected):
    if isinstance(expected, dict):
        test.assertEqual(set(actual), set(expected))
        for key in expected:
            assert_equivalent(test, actual[key], expected[key])
    elif isinstance(expected, list):
        test.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            assert_equivalent(test, a, b)
    elif isinstance(expected, float):
        test.assertAlmostEqual(actual, expected, places=12)
    else:
        test.assertEqual(actual, expected)


class PublishedExamples(unittest.TestCase):
    def test_cli_round_trips_unicode_identifiers(self):
        for identifier in UNICODE_IDS:
            request = {"method": "approval", "candidates": [identifier],
                       "ballots": [{"approvals": [identifier]}]}
            for command, path in ((sys.executable, "python/electoral.py"), ("node", "typescript/cli.ts")):
                with self.subTest(identifier=ascii(identifier), command=command):
                    completed = subprocess.run([command, str(ROOT / path)], input=json.dumps(request),
                                               capture_output=True, text=True, check=True, timeout=30)
                    self.assertEqual(json.loads(completed.stdout), simulate(request))

    def test_criteria_guide_counterexamples(self):
        def ranked(method, rows):
            return simulate({"method": method, "candidates": ["A", "B", "C"],
                             "ballots": [{"ranking": list(order), "count": count} for order, count in rows]})
        self.assertEqual(ranked("plurality", [("ABC", 4), ("BCA", 3), ("CBA", 3)])["winners"], ["A"])
        self.assertEqual(ranked("borda", [("ABC", 6), ("BCA", 4)])["winners"], ["B"])
        self.assertEqual(ranked("instant-runoff", [("ABC", 8), ("BCA", 7), ("CAB", 6)])["winners"], ["A"])
        self.assertEqual(ranked("instant-runoff", [("ABC", 10), ("BCA", 5), ("CAB", 6)])["winners"], ["C"])
        profile = {"candidates": ["A", "B", "C"], "ballots": [
            {"scores": {"A": 5, "B": 4, "C": 4}, "count": 51},
            {"scores": {"A": 0, "B": 5, "C": 5}, "count": 49},
        ]}
        self.assertEqual(simulate({**profile, "method": "score"})["winners"], ["B", "C"])
        self.assertEqual(simulate({**profile, "method": "star"})["winners"], ["B", "C"])
        self.assertEqual(simulate({**profile, "method": "majority-judgment"})["winners"], ["A"])

    def test_every_standalone_program_matches_the_published_response(self):
        """Run every pasteable program, not just the engines they were extracted from."""
        for method in METHOD_IDS:
            expected = json.loads((ROOT / f"examples/responses/{method}.json").read_text())
            request = json.loads((ROOT / f"examples/requests/{method}.json").read_text())
            self.assertEqual(expected["winners"], EXPECTED_WINNERS[method])
            assert_equivalent(self, simulate(request), expected)
            for language, command, extension in (("python", sys.executable, "py"), ("typescript", "node", "ts")):
                with self.subTest(method=method, language=language):
                    path = ROOT / f"examples/{language}/{method}.{extension}"
                    result = subprocess.run([command, str(path)], capture_output=True, text=True, check=True, timeout=30)
                    assert_equivalent(self, json.loads(result.stdout), expected)

    def test_catalog_criteria_and_openapi_cover_every_method(self):
        catalog = json.loads((ROOT / "data/methods.json").read_text())
        criteria = json.loads((ROOT / "data/criteria.json").read_text())
        criterion_ids = {criterion["id"] for criterion in criteria}
        self.assertEqual(len(criterion_ids), 25)
        self.assertEqual([m["id"] for m in catalog], METHOD_IDS)
        for method in catalog:
            self.assertEqual(set(method["criteria"]), criterion_ids)
            for assessment in method["criteria"].values():
                self.assertIn(assessment["status"], {"pass", "fail", "conditional", "unverified", "not-applicable"})
                self.assertTrue(assessment["explanation"])
            chapter = (ROOT / f'site/methods/{method["id"]}.md').read_text()
            self.assertIn("<CodeSelect", chapter)
            self.assertIn("```python", chapter)
            self.assertIn("```typescript", chapter)
        spec = json.loads((ROOT / "site/openapi.json").read_text())
        operation = spec["paths"]["/simulate"]["post"]
        examples = operation["requestBody"]["content"]["application/json"]["examples"]
        responses = operation["responses"]["200"]["content"]["application/json"]["examples"]
        self.assertEqual(set(examples), set(METHOD_IDS))
        self.assertEqual(set(responses), set(METHOD_IDS))
        for method in METHOD_IDS:
            assert_equivalent(self, simulate(examples[method]["value"]), responses[method]["value"])


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class HttpContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def call(self, method, path, data=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        connection.request(method, path, body=json.dumps(data) if data is not None else None,
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status, body = response.status, json.loads(response.read())
        connection.close()
        return status, body

    def test_all_documented_http_examples_execute(self):
        spec = json.loads((ROOT / "site/openapi.json").read_text())
        status, body = self.call("GET", "/systems")
        self.assertEqual(status, 200)
        self.assertEqual(body, spec["paths"]["/systems"]["get"]["responses"]["200"]["content"]["application/json"]["example"])
        operation = spec["paths"]["/simulate"]["post"]
        for method, entry in operation["requestBody"]["content"]["application/json"]["examples"].items():
            with self.subTest(method=method):
                status, body = self.call("POST", "/simulate", entry["value"])
                self.assertEqual(status, 200)
                assert_equivalent(self, body, operation["responses"]["200"]["content"]["application/json"]["examples"][method]["value"])

    def test_http_round_trips_unicode_identifiers(self):
        for identifier in UNICODE_IDS:
            request = {"method": "approval", "candidates": [identifier],
                       "ballots": [{"approvals": [identifier]}]}
            with self.subTest(identifier=ascii(identifier)):
                status, body = self.call("POST", "/simulate", request)
                self.assertEqual(status, 200)
                self.assertEqual(body, simulate(request))

    def test_api_guide_response_and_copyable_clients(self):
        guide = (ROOT / "site/api-design.md").read_text()
        request, response = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", guide, re.S)]
        self.assertEqual(simulate(request), response)
        for language, command, extension in (("python", sys.executable, "py"), ("typescript", "node", "ts")):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                source = re.search(r"```" + language + r"\n(.*?)\n```", guide, re.S)[1]
                source = source.replace("127.0.0.1:8000", "127.0.0.1:" + str(self.server.server_port))
                path = Path(directory) / ("client." + extension)
                path.write_text(source)
                completed = subprocess.run([command, str(path)], capture_output=True, text=True, check=True, timeout=15)
                answer = json.loads(completed.stdout)
                self.assertEqual(answer["winners"], ["B"])
                self.assertEqual(answer["trace"][0]["tally"]["B"], 7)


if __name__ == "__main__":
    unittest.main()
