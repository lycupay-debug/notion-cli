import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from event_bus import Event
from handlers.record_keeper import handle_execution_result


class TestRecordKeeper(unittest.IsolatedAsyncioTestCase):
    async def test_records_all_four_execution_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            for result in ("SUCCESS", "UNCHANGED", "FAILED", "EXECUTE_FAILED"):
                record_id = f"record-{result.lower()}"
                path = task_dir / f"{record_id}.json"
                path.write_text(
                    json.dumps({"record_id": record_id, "task_completed": None}),
                    encoding="utf-8",
                )

                with patch("handlers.record_keeper._TASK_DIR", task_dir):
                    await handle_execution_result(
                        Event(
                            "EXECUTION_RESULT",
                            {"record_id": record_id, "result": result},
                        )
                    )

                task = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(task["task_completed"], result)


if __name__ == "__main__":
    unittest.main()
