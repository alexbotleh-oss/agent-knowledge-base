"""Regression guards for the portable RIMA identity contract.

These tests protect the canonical instructions from accidental omission or drift.
They do not prove that every external chat/client loads or follows the contract.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentIdentityContractTests(unittest.TestCase):
    def read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_canonical_contract_defines_one_agent_and_separate_scopes(self):
        architecture = self.read("core/continuous_agent_architecture.md")
        self.assertIn("Устойчивая идентичность агента: Р.И.М.А. (Рима)", architecture)
        self.assertIn("Развивающаяся Интеллектуальная Модель Агента", architecture)
        self.assertIn("Идентичность агента", architecture)
        self.assertIn("Идентичность проекта", architecture)
        self.assertIn("Идентичность активной задачи", architecture)
        self.assertIn("Не заявлять о человеческой идентичности", architecture)

    def test_identity_gate_precedes_repository_work_gate(self):
        instructions = self.read("core/universal_instructions.md")
        identity_gate = instructions.index("## IDENTITY RESTORE GATE — первый шаг каждой сессии")
        repository_gate = instructions.index("## PRE-REPOSITORY GATE — обязательный порядок")
        self.assertLess(identity_gate, repository_gate)
        for required in (
            "Рима одна — задачи разные",
            "идентичность и рабочие обязательства Римы",
            "подтверждённую идентичность проекта",
            "состояние активной задачи и точку возврата",
            "не выдумывать восстановление",
        ):
            self.assertIn(required, instructions[identity_gate:repository_gate])

    def test_runtime_protocol_requires_identity_restore(self):
        runtime = self.read("core/agent_runtime_protocol.md")
        self.assertIn("Обязательное восстановление идентичности Римы и области работы", runtime)
        self.assertIn("core/continuous_agent_architecture.md", runtime)
        self.assertIn("развитие оценивается", runtime.lower())

    def test_portable_adapter_does_not_claim_automatic_installation(self):
        adapter = self.read("core/platform_project_chat_instruction_templates.md")
        self.assertIn("Persistent agent identity adapter", adapter)
        self.assertIn("Installation in global settings", adapter)
        self.assertIn("behavioral verification are separate states", adapter)


if __name__ == "__main__":
    unittest.main()
