import unittest

from context_trust_gate import authorize_next_step, select_authoritative_checkpoint


class ContextTrustGateTests(unittest.TestCase):
    def _context(self, **overrides):
        context = {
            "freshness_verified": True,
            "semantic_context_usable": True,
            "event_linkage_complete": True,
            "active_goal": "continue memory transfer",
            "next_step": "verify checkpoint conflict",
        }
        context.update(overrides)
        return context

    def test_unverified_context_is_refused_before_action_authorization(self):
        decision = authorize_next_step(self._context(freshness_verified=False))
        self.assertEqual(decision["status"], "REFUSED_UNVERIFIED_CONTEXT")

    def test_unusable_context_is_refused(self):
        decision = authorize_next_step(self._context(semantic_context_usable=False))
        self.assertEqual(decision["status"], "REFUSED_UNUSABLE_CONTEXT")

    def test_incomplete_event_history_requires_confirmation(self):
        decision = authorize_next_step(self._context(event_linkage_complete=False))
        self.assertEqual(decision["status"], "PLAN_REQUIRES_CONFIRMATION")
        self.assertIn("do not infer", decision["reason"])

    def test_unknown_next_step_is_not_authorized(self):
        decision = authorize_next_step(self._context(next_step="UNKNOWN"))
        self.assertEqual(decision["status"], "REFUSED_UNKNOWN_NEXT_STEP")

    def test_only_fully_verified_checkpoint_can_win_over_newer_unverified(self):
        old_verified = {
            "checkpoint_id": "cp-old",
            "timestamp": "2026-10-13T12:00:00Z",
            "freshness_verified": True,
            "semantic_context_usable": True,
            "event_linkage_complete": True,
        }
        new_unverified = {
            "checkpoint_id": "cp-new",
            "timestamp": "2026-10-14T12:00:00Z",
            "freshness_verified": False,
            "semantic_context_usable": False,
            "event_linkage_complete": False,
        }
        selected = select_authoritative_checkpoint([old_verified, new_unverified])
        self.assertEqual(selected["checkpoint_id"], "cp-old")

    def test_no_verified_checkpoint_means_reconciliation_not_guessing(self):
        selected = select_authoritative_checkpoint([
            {
                "checkpoint_id": "cp-new",
                "timestamp": "2026-10-14T12:00:00Z",
                "freshness_verified": True,
                "semantic_context_usable": True,
                "event_linkage_complete": False,
            }
        ])
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
