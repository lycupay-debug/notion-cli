import unittest
from types import SimpleNamespace
from unittest.mock import patch

from listeners.system_ledger import execute_system_ledger


class TestSystemLedgerChannel(unittest.IsolatedAsyncioTestCase):
    async def test_channel_adapter_reads_data_source_id_from_task(self):
        task = SimpleNamespace(record_id="record-123")
        task_data = {
            "record_id": "record-123",
            "parent": {
                "data_source_id": "data-source-456",
            },
        }

        with patch(
            "methods.read_json_file.read_json_file",
            return_value=task_data,
        ), patch(
            "listeners.system_ledger.SystemLedgerListener.handle",
            return_value={
                "status": "UPDATED",
                "page_id": "data-source-456",
                "verified": True,
            },
        ) as handle:
            result = await execute_system_ledger(task)

        handle.assert_called_once_with("data-source-456")
        self.assertEqual(result["status"], "UPDATED")

    async def test_channel_adapter_rejects_missing_record_id(self):
        task = SimpleNamespace(record_id="")

        with self.assertRaises(ValueError):
            await execute_system_ledger(task)

    async def test_channel_adapter_rejects_missing_data_source_id(self):
        task = SimpleNamespace(record_id="record-123")
        with patch(
            "methods.read_json_file.read_json_file",
            return_value={"record_id": "record-123", "parent": {}},
        ):
            with self.assertRaises(ValueError):
                await execute_system_ledger(task)


if __name__ == "__main__":
    unittest.main()
