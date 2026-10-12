import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MemoryValidationTests(unittest.TestCase):
    def test_memory_validation_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/validate_memory.py")],
            cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MEMORY VALIDATION: PASS", result.stdout)

if __name__ == "__main__":
    unittest.main()
