import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "generate_report.sh"


class GenerateReportTargetGuardTests(unittest.TestCase):
    def test_refuses_canonical_target_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            handoff = project / "HANDOFF.md"
            original = "# HANDOFF\nDo not overwrite.\n"
            handoff.write_text(original, encoding="utf-8")

            result = subprocess.run(
                ["bash", str(SCRIPT), str(project), str(handoff)],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Refusing to overwrite canonical memory file", result.stderr)
            self.assertEqual(handoff.read_text(encoding="utf-8"), original)

    def test_allows_derived_report_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            report = project / "validation-report.md"

            result = subprocess.run(
                ["bash", str(SCRIPT), str(project), str(report)],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertTrue(report.is_file(), result.stdout + result.stderr)
            self.assertIn("# Validation report", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
