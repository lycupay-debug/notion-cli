import unittest
from types import SimpleNamespace
from unittest.mock import patch

from listeners.system_ledger import execute_system_ledger


class TestSystemLedgerChannel(unittest.IsolatedAsyncioTestCase):
    async def test_channel_adapter_uses_legacy_listener(self):
        task = SimpleNamespace(record_id="page-123")

        with patch(
            "listeners.system_ledger.SystemLedgerListener.handle",
            return_value={
                "status": "UPDATED",
                "page_id": "page-123",
                "verified": True,
            },
        ) as handle:
            result = await execute_system_ledger(task)

        handle.assert_called_once_with("page-123")
        self.assertEqual(result["status"], "UPDATED")
        self.assertTrue(result["verified"])

    async def test_channel_adapter_rejects_missing_record_id(self):
        task = SimpleNamespace(record_id="")

        with self.assertRaises(ValueError):
            await execute_system_ledger(task)


if __name__ == "__main__":
    unittest.main()
