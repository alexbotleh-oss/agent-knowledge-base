import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import memory_aware_session_restore as restore


class MemoryAwareRestorePartialStatusTests(unittest.TestCase):
    def test_partial_task_packet_does_not_hide_unavailable_memory(self):
        base = {
            "status": "PARTIAL",
            "project_scope": {
                "task_project_id": "AGENT_MEMORY_SYSTEM",
                "handoff_project_id": "AGENT_MEMORY_SYSTEM",
                "event_log_project_id": "AGENT_MEMORY_SYSTEM",
            },
            "warnings": [],
        }
        unavailable = {"status": "STALE", "coverage_status": "UNKNOWN", "records": []}
        with mock.patch.object(restore, "build_verified_session_packet", return_value=base), \
             mock.patch.object(restore, "retrieve_approved_memory", return_value=unavailable):
            packet = restore.build_memory_aware_packet(
                Path("projects/AGENT_MEMORY_SYSTEM/TASK_STATE.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/HANDOFF.md"),
                Path("projects/AGENT_MEMORY_SYSTEM/events.jsonl"),
                "alexbotleh-oss/agent-knowledge-base",
            )
        self.assertEqual(packet["status"], "PARTIAL_WITH_MEMORY_UNAVAILABLE")
        self.assertEqual(packet["semantic_memory"]["status"], "STALE")


if __name__ == "__main__":
    unittest.main()
