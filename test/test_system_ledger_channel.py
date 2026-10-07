import unittest
from types import SimpleNamespace
from unittest.mock import patch

from listeners.system_ledger import execute_system_ledger


class TestSystemLedgerChannel(unittest.IsolatedAsyncioTestCase):
    async def test_channel_adapter_reads_entity_page_id_from_task(self):
        task = SimpleNamespace(record_id="record-123")
        task_data = {
            "record_id": "record-123",
            "parent": {
                "data_source_id": "data-source-456",
            },
            "entity": {
                "id": "page-789",
                "type": "page",
            },
        }

        with patch(
            "methods.read_json_file.read_json_file",
            return_value=task_data,
        ), patch(
            "listeners.system_ledger.SystemLedgerListener.handle",
            return_value={
                "status": "UPDATED",
                "page_id": "page-789",
                "verified": True,
            },
        ) as handle:
            result = await execute_system_ledger(task)

        handle.assert_called_once_with("page-789")
        self.assertEqual(result["status"], "UPDATED")

    async def test_channel_adapter_does_not_use_data_source_id_as_page_id(self):
        task = SimpleNamespace(record_id="record-123")
        task_data = {
            "record_id": "record-123",
            "parent": {
                "data_source_id": "data-source-456",
            },
            "entity": {
                "id": "page-789",
                "type": "page",
            },
        }

        with patch(
            "methods.read_json_file.read_json_file",
            return_value=task_data,
        ), patch(
            "listeners.system_ledger.SystemLedgerListener.handle",
            return_value={
                "status": "UNCHANGED",
                "page_id": "page-789",
            },
        ) as handle:
            await execute_system_ledger(task)

        called_page_id = handle.call_args.args[0]
        self.assertEqual(called_page_id, "page-789")
        self.assertNotEqual(called_page_id, "data-source-456")

    async def test_channel_adapter_rejects_missing_record_id(self):
        task = SimpleNamespace(record_id="")

        with self.assertRaises(ValueError):
            await execute_system_ledger(task)

    async def test_channel_adapter_rejects_missing_entity_id(self):
        task = SimpleNamespace(record_id="record-123")
        with patch(
            "methods.read_json_file.read_json_file",
            return_value={
                "record_id": "record-123",
                "parent": {
                    "data_source_id": "data-source-456",
                },
                "entity": {},
            },
        ):
            with self.assertRaises(ValueError):
                await execute_system_ledger(task)


if __name__ == "__main__":
    unittest.main()
