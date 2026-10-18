import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UnifiedMemoryControlLoopContractTests(unittest.TestCase):
    def test_runtime_protocol_links_the_unified_contract(self):
        runtime = (ROOT / "core/agent_runtime_protocol.md").read_text(encoding="utf-8")
        self.assertIn("core/unified_memory_control_loop.md", runtime)

    def test_contract_has_stable_acceptance_matrix(self):
        contract = (ROOT / "core/unified_memory_control_loop.md").read_text(encoding="utf-8")
        for test_id in (f"UMC-{i:02d}" for i in range(1, 13)):
            self.assertIn(test_id, contract)
        self.assertIn("Definition of done before test stage", contract)
        self.assertIn("Shared memory supplies evidence", contract)
        self.assertIn("UNKNOWN", contract)
        self.assertIn("append-only", contract.lower())

    def test_contract_does_not_claim_all_runtime_capabilities_are_deployed(self):
        contract = (ROOT / "core/unified_memory_control_loop.md").read_text(encoding="utf-8")
        self.assertIn("does not claim that every runtime mechanism is deployed", contract)
        self.assertIn("not ready for end-to-end testing", contract)
        self.assertIn("no automatic cross-chat capture is claimed", contract)


if ( __name__ == "__main__"):
    unittest.main()
