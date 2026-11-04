"""Ensure parity checks enforce fixture validity, not just engine agreement."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
check_multi_parity = importlib.import_module("check_multi_parity")
check_parity = importlib.import_module("check_parity")


class ParityCheckerTests(unittest.TestCase):
    def run_checker(self, module, python_valid=True, node_valid=True,
                    python_invalid=False, node_invalid=False, node_status=400):
        request = {"method": "approval", "candidates": ["A"],
                   "ballots": [{"approvals": ["A"]}]}
        if module is check_multi_parity:
            request["seats"] = 1
        result = module.simulate(request)
        rejected = {"ok": False, "status": node_status}
        accepted = {"ok": True, "result": result}
        python_answers = [result if valid else module.ElectionError("Rejected", 400)
                          for valid in (python_valid, python_invalid)]
        node_answers = [accepted if valid else rejected for valid in (node_valid, node_invalid)]
        output = io.StringIO()
        with patch.object(module, "valid_profiles", return_value=iter([request])), \
             patch.object(module, "invalid_profiles", return_value=iter([{}])), \
             patch.object(module, "simulate", side_effect=python_answers), \
             patch.object(module.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(node_answers))), \
             contextlib.redirect_stdout(output):
            module.main()
        return output.getvalue()

    def test_correct_valid_and_invalid_results_pass(self):
        for module in (check_parity, check_multi_parity):
            with self.subTest(module=module.__name__):
                output = self.run_checker(module)
                self.assertIn("1 valid profiles", output)
                self.assertIn("1 invalid profiles", output)

    def test_shared_rejection_of_valid_profiles_fails(self):
        for module in (check_parity, check_multi_parity):
            with self.subTest(module=module.__name__), self.assertRaisesRegex(AssertionError, "valid profile was rejected"):
                self.run_checker(module, python_valid=False, node_valid=False)

    def test_shared_acceptance_of_invalid_profiles_fails(self):
        for module in (check_parity, check_multi_parity):
            with self.subTest(module=module.__name__), self.assertRaisesRegex(AssertionError, "invalid profile was unexpectedly accepted"):
                self.run_checker(module, python_invalid=True, node_invalid=True)

    def test_engines_must_agree_on_validity(self):
        for module in (check_parity, check_multi_parity):
            for mutation in ({"node_valid": False}, {"python_valid": False},
                             {"node_invalid": True}, {"python_invalid": True}):
                with self.subTest(module=module.__name__, mutation=mutation), self.assertRaises(AssertionError):
                    self.run_checker(module, **mutation)

    def test_engines_must_agree_on_error_status(self):
        for module in (check_parity, check_multi_parity):
            with self.subTest(module=module.__name__), self.assertRaises(AssertionError):
                self.run_checker(module, node_status=413)


if __name__ == "__main__":
    unittest.main()
