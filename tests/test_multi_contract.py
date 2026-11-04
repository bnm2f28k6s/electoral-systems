"""Execute every published committee example and verify the live HTTP contract."""
import copy
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
from multi_winner import simulate
from multi_fixtures import METHOD_IDS, EXPECTED_WINNERS
from test_contract import assert_equivalent, QuietHandler


class MultiPublishedExamples(unittest.TestCase):
    def test_all_standalone_committee_programs(self):
        for method in METHOD_IDS:
            request = json.loads((ROOT / f"examples/multi/requests/{method}.json").read_text())
            expected = json.loads((ROOT / f"examples/multi/responses/{method}.json").read_text())
            self.assertEqual(expected["winners"], EXPECTED_WINNERS[method])
            self.assertEqual(len(expected["winners"]), expected["seats"])
            self.assertEqual(len(set(expected["winners"])), expected["seats"])
            assert_equivalent(self, simulate(request), expected)
            for language, command, extension in (("python", sys.executable, "py"), ("typescript", "node", "ts")):
                with self.subTest(method=method, language=language):
                    path = ROOT / f"examples/multi/{language}/{method}.{extension}"
                    completed = subprocess.run([command, str(path)], capture_output=True, text=True, check=True, timeout=30)
                    assert_equivalent(self, json.loads(completed.stdout), expected)

    def test_all_source_criteria_and_method_rows_are_covered(self):
        catalog = json.loads((ROOT / "data/multi_methods.json").read_text())
        criteria = json.loads((ROOT / "data/multi_criteria.json").read_text())
        # Every source result/strategy column and definition distinction, plus
        # committee counting and approval-specific representation properties.
        required = {"proportionality-solid-coalitions", "solid-coalition", "candidate-monotonicity",
                    "support-monotonicity", "weak-pareto", "strong-pareto", "consensus-committee",
                    "fishburn-condorcet", "gehrlein-condorcet", "condorcet-winning-set", "smith",
                    "committee-monotonicity", "iia", "consistency", "participation", "clone-independence",
                    "homogeneity", "favorite-betrayal", "semi-honest", "universally-liked",
                    "weak-unanimity", "strong-unanimity", "fixed-majority", "polynomial-time",
                    "summability", "jr", "pjr", "ejr"}
        self.assertEqual({c["id"] for c in criteria}, required)
        self.assertEqual([m["id"] for m in catalog], METHOD_IDS)
        for method in catalog:
            self.assertEqual(set(method["criteria"]), required)
            for assessment in method["criteria"].values():
                self.assertIn(assessment["status"], {"pass", "fail", "conditional", "unverified", "not-applicable"})
                self.assertTrue(assessment["explanation"])
            page = (ROOT / f'site/multi-methods/{method["id"]}.md').read_text()
            self.assertIn("```python", page)
            self.assertIn("```typescript", page)
            self.assertIn("<CodeSelect", page)

    def test_actual_quota_variants_can_fail_homogeneity(self):
        profiles = [
            ("stv", "ABCD", 3, [("BCAD", 1), ("DABC", 5), ("BDCA", 7)], ["A", "B", "D"], ["B", "C", "D"]),
            ("expanding-approvals", "ABC", 2, [("BCA", 1), ("CAB", 14), ("CBA", 12)], ["B", "C"], ["A", "C"]),
        ]
        for method, candidates, seats, rows, original, tripled in profiles:
            with self.subTest(method=method):
                request = {"method": method, "candidates": list(candidates), "seats": seats,
                           "ballots": [{"ranking": list(order), "count": count} for order, count in rows]}
                before = simulate(request)
                self.assertEqual(before["winners"], original)
                self.assertFalse(before["tie"])
                scaled = copy.deepcopy(request)
                for ballot in scaled["ballots"]:
                    ballot["count"] *= 3
                after = simulate(scaled)
                self.assertEqual(after["winners"], tripled)
                self.assertFalse(after["tie"])


class MultiHttpContract(unittest.TestCase):
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

    def test_every_committee_openapi_example_executes(self):
        spec = json.loads((ROOT / "site/openapi.json").read_text())
        status, body = self.call("GET", "/multi/systems")
        self.assertEqual(status, 200)
        self.assertEqual(body, spec["paths"]["/multi/systems"]["get"]["responses"]["200"]["content"]["application/json"]["example"])
        operation = spec["paths"]["/multi/simulate"]["post"]
        examples = operation["requestBody"]["content"]["application/json"]["examples"]
        responses = operation["responses"]["200"]["content"]["application/json"]["examples"]
        self.assertEqual(set(examples), set(METHOD_IDS))
        self.assertEqual(set(responses), set(METHOD_IDS))
        for method, entry in examples.items():
            with self.subTest(method=method):
                status, body = self.call("POST", "/multi/simulate", entry["value"])
                self.assertEqual(status, 200)
                assert_equivalent(self, body, responses[method]["value"])

    def test_validation_errors_and_separate_single_winner_route(self):
        request = {"method": "approval", "candidates": ["A", "B"], "seats": 2,
                   "ballots": [{"approvals": ["A", "B"]}]}
        status, body = self.call("POST", "/multi/simulate", request)
        self.assertEqual(status, 200)
        self.assertEqual(body["winners"], ["A", "B"])
        self.assertFalse(body["tie"])
        self.assertEqual(self.call("POST", "/simulate", request)[0], 400)
        self.assertEqual(self.call("POST", "/multi/simulate", {**request, "seats": 3})[0], 400)
        large = {"method": "proportional-approval", "candidates": list("ABCDEFGHI"), "seats": 2,
                 "ballots": [{"approvals": ["A"]}]}
        self.assertEqual(self.call("POST", "/multi/simulate", large)[0], 413)

    def test_committee_guide_response_and_copyable_clients(self):
        guide = (ROOT / "site/multi-api.md").read_text()
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
                self.assertEqual(answer["winners"], ["A", "D"])
                self.assertEqual(answer["seats"], 2)


if __name__ == "__main__":
    unittest.main()
