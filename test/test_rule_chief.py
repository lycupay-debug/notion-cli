import unittest

from rule_chief import RuleChief


class TestRuleChief(unittest.TestCase):
    def test_missing_data_source_is_not_routed(self):
        decision = RuleChief().decide({"record_id": "r1", "parent": {}})
        self.assertEqual(decision.status, "UNROUTED")
        self.assertEqual(decision.reason, "DATA_SOURCE_ID_MISSING")

    def test_missing_rule_is_not_guessed(self):
        task = {
            "record_id": "r1",
            "parent": {"data_source_id": "ds1"},
        }
        decision = RuleChief().decide(task)
        self.assertEqual(decision.status, "UNROUTED")
        self.assertEqual(decision.reason, "NO_RULE_CONFIGURED")
        self.assertIsNone(decision.assignee)
        self.assertIsNone(decision.channel)

    def test_explicit_rule_routes(self):
        task = {
            "record_id": "r1",
            "parent": {"data_source_id": "ds1"},
        }
        chief = RuleChief(
            {
                "ds1": {
                    "enabled": True,
                    "assignee": "system-ledger",
                    "channel": "system_ledger",
                }
            }
        )
        decision = chief.decide(task)
        self.assertEqual(decision.status, "ROUTED")
        self.assertEqual(decision.assignee, "system-ledger")
        self.assertEqual(decision.channel, "system_ledger")

    def test_incomplete_rule_is_not_routed(self):
        task = {
            "record_id": "r1",
            "parent": {"data_source_id": "ds1"},
        }
        decision = RuleChief(
            {"ds1": {"enabled": True, "channel": "system_ledger"}}
        ).decide(task)
        self.assertEqual(decision.status, "UNROUTED")
        self.assertEqual(decision.reason, "RULE_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
