"""Real HTTP family routes, canonical validation, schemas, and TS parity."""
import copy
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from http.server import HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python"), str(ROOT / "scripts")]
from api import FAMILY_METHODS, MULTI_FAMILY_METHODS, FIELDS
from electoral import simulate
from multi_winner import simulate as simulate_multi
from fixtures import example_request
from multi_fixtures import example_request as multi_example
from server import Handler
import api


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


def cases():
    for prefix, catalog, fixture, engine in [
        ("/simulate", FAMILY_METHODS, example_request, simulate),
        ("/multi/simulate", MULTI_FAMILY_METHODS, multi_example, simulate_multi),
    ]:
        for family, methods in catalog.items():
            for method in methods:
                request = fixture(method)
                if family == "marked":
                    for ballot in request["ballots"]:
                        ranking = ballot.pop("ranking")
                        ballot["choice"] = ranking[-1] if method == "anti-plurality" else ranking[0]
                yield prefix, family, request, engine


class FamilyApi(unittest.TestCase):
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

    def post(self, path, request, raw=False, content_type="application/json", length=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=15)
        headers = {"Content-Type": content_type}
        if length is not None:
            headers["Content-Length"] = str(length)
        conn.request("POST", path, request if raw else json.dumps(request), headers)
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def test_all_fixtures_and_compatible_formats(self):
        for prefix, family, request, engine in cases():
            with self.subTest(prefix=prefix, family=family, method=request["method"]):
                expected = engine(request)
                self.assertEqual(self.post(prefix + "/" + family, request), (200, expected))
                self.assertEqual(self.post(prefix, request), (200, expected))

    def test_wrong_family_even_with_empty_ballots(self):
        for prefix, family, request, _ in cases():
            catalogs = MULTI_FAMILY_METHODS if prefix.startswith("/multi") else FAMILY_METHODS
            for wrong, methods in catalogs.items():
                if request["method"] in methods:
                    continue
                for ballots in [request["ballots"], []]:
                    with self.subTest(prefix=prefix, method=request["method"], wrong=wrong):
                        status, body = self.post(prefix + "/" + wrong, {**request, "ballots": ballots})
                        self.assertEqual(status, 400)
                        self.assertIn("compatible", body["error"])

    def test_mixed_formats_legacy_preserved(self):
        for prefix, methods, fixture, engine in [
            ("/simulate", FAMILY_METHODS["marked"], example_request, simulate),
            ("/multi/simulate", MULTI_FAMILY_METHODS["marked"], multi_example, simulate_multi),
        ]:
            for method in methods:
                request = fixture(method)
                ballot = request["ballots"][0]
                ranking = ballot.pop("ranking")
                ballot["choice"] = ranking[-1] if method == "anti-plurality" else ranking[0]
                self.assertEqual(self.post(prefix, request), (200, engine(request)))
                for family in ["ranked", "marked"]:
                    self.assertEqual(self.post(prefix + "/" + family, request)[0], 400)

    def test_facades_delegate_to_specialized_functions(self):
        for prefix, family, request, engine in cases():
            name = "simulate_" + ("multi_" if prefix.startswith("/multi") else "") + family
            facade = api.simulate_multi_request if prefix.startswith("/multi") else api.simulate_request
            specialized = getattr(api, name)
            self.assertEqual(specialized(request), engine(request))
            with patch.object(api, name, wraps=specialized) as delegated:
                self.assertEqual(facade(request), engine(request))
                delegated.assert_called_once_with(request)

    def test_malformed_options_and_limits_every_route(self):
        for prefix, family, request, _ in cases():
            path = prefix + "/" + family
            for invalid in [None, [], {**request, "options": None}, {**request, "options": {"unknown": 1}},
                            {**request, "options": {"seed": -1}}, {**request, "ballots": None},
                            {**request, "unexpected": True}, {**request, "method": []}]:
                self.assertEqual(self.post(path, invalid)[0], 400)
            self.assertEqual(self.post(path, "{", raw=True)[0], 400)
            self.assertEqual(self.post(path, request, content_type="text/plain")[0], 415)
            self.assertEqual(self.post(path, {**request, "candidates": [str(i) for i in range(33)]})[0], 413)
            self.assertEqual(self.post(path, "", raw=True, length=1024 * 1024 + 1)[0], 413)
            if family != "none":
                malformed = copy.deepcopy(request)
                malformed["ballots"][0]["count"] = True
                self.assertEqual(self.post(path, malformed)[0], 400)
                too_many = copy.deepcopy(request)
                too_many["ballots"][0]["count"] = 1000000
                self.assertEqual(self.post(path, too_many)[0], 413)
        self.assertEqual(self.post("/simulate/cumulative", {})[0], 404)
        self.assertEqual(self.post("/multi/simulate/quadratic", {})[0], 404)

    def test_openapi_exact_family_unions(self):
        spec = json.loads((ROOT / "site/openapi.json").read_text())
        schemas = spec["components"]["schemas"]
        for prefix, catalog in [("/simulate", FAMILY_METHODS), ("/multi/simulate", MULTI_FAMILY_METHODS)]:
            for family, methods in catalog.items():
                operation = spec["paths"][prefix + "/" + family]["post"]
                ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                union = schemas[ref.split("/")[-1]]
                seen = set()
                for member in union["oneOf"]:
                    schema = schemas[member["$ref"].split("/")[-1]]
                    self.assertFalse(schema["additionalProperties"])
                    seen.update(schema["properties"]["method"]["enum"])
                    ballots = schema["properties"]["ballots"]
                    if family == "none":
                        self.assertEqual(ballots["maxItems"], 0)
                    else:
                        ballot = schemas[ballots["items"]["$ref"].split("/")[-1]]
                        self.assertEqual(ballot["required"], [FIELDS[family]])
                self.assertEqual(seen, set(methods))

    def test_specialized_openapi_examples_execute(self):
        spec = json.loads((ROOT / "site/openapi.json").read_text())
        for prefix, catalog, engine in [("/simulate", FAMILY_METHODS, simulate),
                                        ("/multi/simulate", MULTI_FAMILY_METHODS, simulate_multi)]:
            for family, methods in catalog.items():
                path = prefix + "/" + family
                examples = spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["examples"]
                self.assertEqual(set(examples), set(methods))
                for method, example in examples.items():
                    with self.subTest(path=path, method=method):
                        request = example["value"]
                        self.assertEqual(self.post(path, request), (200, engine(request)))

    def test_typescript_python_parity(self):
        payload = [{"multi": prefix.startswith("/multi"), "family": family, "request": request,
                    "expected": engine(request)} for prefix, family, request, engine in cases()]
        completed = subprocess.run(["node", "tests/test_family_api.ts"], cwd=ROOT,
                                   input=json.dumps(payload), text=True, capture_output=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
