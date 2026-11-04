"""Run all generated Go examples and exercise the real JSON CLI boundary."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_go_parity
from test_contract import assert_equivalent


class GoPublishedExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="electoral-go-contract-")
        cls.binaries = {}
        for family, command in (("single", "electoral"), ("multi", "multi")):
            binary = str(Path(cls.directory.name) / command)
            subprocess.run(["go", "build", "-o", binary, "./cmd/" + command], cwd=ROOT / "go", check=True)
            cls.binaries[family] = binary
        cls.addClassCleanup(cls.directory.cleanup)

    def test_all_standalone_programs_and_cli_results(self):
        executed = 0
        for family, catalog, prefix, chapters in (
            ("single", "methods", "examples", "methods"),
            ("multi", "multi_methods", "examples/multi", "multi-methods"),
        ):
            methods = json.loads((ROOT / f"data/{catalog}.json").read_text())
            files = {path.stem for path in (ROOT / prefix / "go").glob("*.go")}
            self.assertEqual(files, {method["id"] for method in methods})
            for method in methods:
                ident = method["id"]
                with self.subTest(family=family, method=ident):
                    path = ROOT / prefix / "go" / (ident + ".go")
                    expected = json.loads((ROOT / prefix / "responses" / (ident + ".json")).read_text())
                    request = (ROOT / prefix / "requests" / (ident + ".json")).read_text()
                    page = (ROOT / "site" / chapters / (ident + ".md")).read_text()
                    snippet = re.search(r"```go\n(.*?)\n```", page, re.S)
                    self.assertIsNotNone(snippet)
                    assert snippet is not None
                    self.assertEqual(snippet[1] + "\n", path.read_text())
                    # Run outside the repository to prove there are no project imports.
                    standalone = subprocess.run(["go", "run", str(path)], cwd=self.directory.name,
                                                capture_output=True, text=True, check=True, timeout=60)
                    assert_equivalent(self, json.loads(standalone.stdout), expected)
                    counted = subprocess.run([self.binaries[family]], input=request,
                                             capture_output=True, text=True, check=True, timeout=30)
                    assert_equivalent(self, json.loads(counted.stdout), expected)
                    executed += 1
        self.assertEqual(executed, 44)

    def test_scalar_unicode_identifiers_are_preserved(self):
        for family, binary in self.binaries.items():
            for identifier in ("🌱", "🌱" * 100, "\ufeff", "�", "A\\ud800B"):
                request = {"method": "approval", "candidates": [identifier], "ballots": [{"approvals": [identifier]}]}
                if family == "multi":
                    request["seats"] = 1
                for ensure_ascii in (True, False):
                    with self.subTest(family=family, identifier=identifier, ensure_ascii=ensure_ascii):
                        result = subprocess.run([binary], input=json.dumps(request, ensure_ascii=ensure_ascii),
                                                capture_output=True, text=True, check=True, timeout=10)
                        self.assertEqual(json.loads(result.stdout)["winners"], [identifier])

    def test_json_errors_are_explicit_and_do_not_count(self):
        for family, binary in self.binaries.items():
            for data in (b"", b"{} {}", b"null", b"{", b'"\xff"',
                         b'{"method":"approval","candidates":["\\ud800"],"ballots":[{"approvals":["\\ud800"]}]}',
                         b'{"method":"approval","candidates":["A"],"ballots":[{"scores":{"\\udfff":1}}]}'):
                with self.subTest(family=family, data=data):
                    result = subprocess.run([binary], input=data, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, b"")
                    self.assertEqual(json.loads(result.stderr)["status"], 400)


class GoParityCheckerTests(unittest.TestCase):
    def test_checker_rejects_shared_rejection_and_acceptance(self):
        for module in (check_go_parity.check_parity, check_go_parity.check_multi_parity):
            with self.subTest(module=module.__name__):
                error = module.ElectionError("Rejected", 400)
                with patch.object(module, "simulate", side_effect=error):
                    with self.assertRaisesRegex(AssertionError, "valid profile was rejected"):
                        check_go_parity.verify(module, [{}], [], [{"ok": False, "status": 400}])
                with patch.object(module, "simulate", return_value={}):
                    with self.assertRaisesRegex(AssertionError, "invalid profile was unexpectedly accepted"):
                        check_go_parity.verify(module, [], [{}], [{"ok": True, "result": {}}])
                    with self.assertRaises(AssertionError):
                        check_go_parity.verify(module, [{}], [], [{"ok": False, "status": 400}])
                with patch.object(module, "simulate", side_effect=error):
                    with self.assertRaises(AssertionError):
                        check_go_parity.verify(module, [], [{}], [{"ok": False, "status": 413}])


if __name__ == "__main__":
    unittest.main()
