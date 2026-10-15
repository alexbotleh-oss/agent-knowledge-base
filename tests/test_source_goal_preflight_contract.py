"""Guard the source-and-goal preflight documentation wiring.

This is a documentation-contract smoke test only. It does NOT prove that a
language model will follow the instructions in a live conversation.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceGoalPreflightContractTests(unittest.TestCase):
    def test_universal_instructions_define_the_preflight(self):
        text = (ROOT / "core" / "universal_instructions.md").read_text(encoding="utf-8")
        self.assertIn("SOURCE-AND-GOAL PREFLIGHT", text)
        for status in (
            "FOUND", "READ", "EXTRACTED", "ANALYZED_PARTIAL",
            "ANALYZED_COMPLETE", "VERIFIED", "NOT_AVAILABLE_HERE", "BLOCKED",
        ):
            self.assertIn(f"`{status}`", text)

    def test_runtime_protocol_wires_the_preflight(self):
        text = (ROOT / "core" / "agent_runtime_protocol.md").read_text(encoding="utf-8")
        self.assertIn("SOURCE-AND-GOAL PREFLIGHT", text)
        self.assertIn("core/universal_instructions.md", text)

    def test_incident_has_current_and_historical_only_cases(self):
        text = (
            ROOT / "projects" / "AGENT_MEMORY_SYSTEM" /
            "SOURCE_AND_GOAL_PREFLIGHT_INCIDENT_2026-10-14.md"
        ).read_text(encoding="utf-8")
        self.assertIn("CTX-01", text)
        self.assertIn("CTX-02", text)
        self.assertIn("does not establish the exact internal cause", text)

    def test_lesson_warns_that_documentation_is_not_behavioral_proof(self):
        text = (ROOT / "projects" / "AGENT_MEMORY_SYSTEM" / "LESSONS.md").read_text(encoding="utf-8")
        self.assertIn("L-AGMS-20261014-003", text)
        self.assertIn("не доказывает, что поведение модели автоматически изменилось", text)


if __name__ == "__main__":
    unittest.main()
