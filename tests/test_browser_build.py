"""Browser compilation recipe and stale-artifact regression checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import browser_engine


class BrowserBuildTests(unittest.TestCase):
    def test_compiler_recipe_and_manifest_fail_closed(self):
        # This fixture tests build plumbing, not compilation or election counts.
        # tests/test_browser_engine.mjs exercises real emitted output after a build.
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)

            def emit_fixture(command, **kwargs):
                self.assertIn("typescript@5.9.3", command)
                self.assertEqual(kwargs["env"]["npm_config_ignore_scripts"], "true")
                self.assertTrue(kwargs["check"])
                target = Path(command[command.index("--outDir") + 1])
                for name in browser_engine.MODULES:
                    (target / name).write_text("// build-plumbing fixture\n")

            with patch.object(browser_engine.subprocess, "run", side_effect=emit_fixture) as run:
                target = browser_engine.compile_browser(out)
                run.assert_called_once()
            browser_engine.check_browser(out)
            manifest = json.loads((target / "manifest.json").read_text())
            self.assertEqual(set(manifest["sources"]), set(browser_engine.SOURCES))
            self.assertEqual(set(manifest["modules"]), set(browser_engine.MODULES))
            with patch.object(browser_engine, "COMPILER", "wrong-version"):
                with self.assertRaisesRegex(AssertionError, "compiler"):
                    browser_engine.check_browser(out)
            (target / "api.js").write_text("// changed\n")
            with self.assertRaisesRegex(AssertionError, "modules"):
                browser_engine.check_browser(out)

    def test_emit_config_rewrites_imports_without_source_maps(self):
        config = json.loads((ROOT / "typescript/tsconfig.browser.json").read_text())
        self.assertTrue(config["compilerOptions"]["rewriteRelativeImportExtensions"])
        self.assertFalse(config["compilerOptions"]["noEmit"])
        self.assertFalse(config["compilerOptions"]["sourceMap"])
        self.assertEqual(config["include"], ["electoral.ts", "multi_winner.ts", "api.ts"])


if __name__ == "__main__":
    unittest.main()
