import asyncio
import unittest
from unittest.mock import patch

from channel import ChannelManager, ChannelTask


class TestChannelManager(unittest.IsolatedAsyncioTestCase):
    async def test_same_resource_is_serial(self):
        manager = ChannelManager()
        running = 0
        max_running = 0
        order = []

        async def executor(task):
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            order.append(f"start:{task.record_id}")
            await asyncio.sleep(0.02)
            order.append(f"end:{task.record_id}")
            running -= 1
            return {"status": "UNCHANGED"}

        with patch("channel.manager.load_callable", return_value=executor), patch("event_bus.publish_default"):
            manager.load_config({"channels": {"a": {
                "enabled": True, "max_workers": 4,
                "module": "unused", "function": "unused",
            }}})
            await manager.submit(ChannelTask("1", "u", "a", {"entity": {"id": "page-1"}}))
            await manager.submit(ChannelTask("2", "u", "a", {"entity": {"id": "page-1"}}))
            await manager.wait_for_idle("a")

        self.assertEqual(max_running, 1)
        self.assertEqual(order, ["start:1", "end:1", "start:2", "end:2"])

    async def test_different_resources_in_same_channel_run_in_parallel(self):
        manager = ChannelManager()
        started = asyncio.Event()
        release = asyncio.Event()
        active = 0
        max_active = 0

        async def executor(task):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            if active == 2:
                started.set()
            await release.wait()
            active -= 1
            return {"status": "UNCHANGED"}

        with patch("channel.manager.load_callable", return_value=executor), patch("event_bus.publish_default"):
            manager.load_config({"channels": {"a": {
                "enabled": True, "max_workers": 2,
                "module": "unused", "function": "unused",
            }}})
            await manager.submit(ChannelTask("1", "u", "a", {"entity": {"id": "page-1"}}))
            await manager.submit(ChannelTask("2", "u", "a", {"entity": {"id": "page-2"}}))
            await asyncio.wait_for(started.wait(), timeout=1)

        self.assertEqual(max_active, 2)
        release.set()
        await manager.wait_for_idle("a")

    async def test_different_channels_can_run_in_parallel(self):
        manager = ChannelManager()
        release = asyncio.Event()
        active = 0
        max_active = 0

        async def executor(task):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await release.wait()
            active -= 1
            return {"status": "UNCHANGED"}

        with patch("channel.manager.load_callable", return_value=executor), patch("event_bus.publish_default"):
            manager.load_config({"channels": {
                "a": {"enabled": True, "max_workers": 1, "module": "unused", "function": "unused"},
                "b": {"enabled": True, "max_workers": 1, "module": "unused", "function": "unused"},
            }})
            await manager.submit(ChannelTask("1", "u", "a", {}))
            await manager.submit(ChannelTask("2", "u", "b", {}))
            await asyncio.sleep(0.02)

        self.assertEqual(max_active, 2)
        release.set()
        await manager.wait_for_idle("a")
        await manager.wait_for_idle("b")

    async def test_execution_result_is_published_and_next_task_starts(self):
        manager = ChannelManager()
        order = []

        async def executor(task):
            order.append(f"execute:{task.record_id}")
            return {"status": "SUCCESS"}

        def publish(event):
            order.append(f"publish:{event.data['record_id']}:{event.data['result']}")
            return asyncio.create_task(asyncio.sleep(0))

        with patch("channel.manager.load_callable", return_value=executor), patch("event_bus.publish_default", side_effect=publish):
            manager.load_config({"channels": {"a": {
                "enabled": True, "max_workers": 1,
                "module": "unused", "function": "unused",
            }}})
            await manager.submit(ChannelTask("1", "u", "a", {}))
            await manager.submit(ChannelTask("2", "u", "a", {}))
            await manager.wait_for_idle("a")

        self.assertEqual(order, [
            "execute:1", "publish:1:SUCCESS",
            "execute:2", "publish:2:SUCCESS",
        ])

    async def test_execute_exception_publishes_execute_failed_and_next_task_runs(self):
        manager = ChannelManager()
        order = []

        async def executor(task):
            order.append(f"execute:{task.record_id}")
            if task.record_id == "1":
                raise RuntimeError("boom")
            return {"status": "UNCHANGED"}

        def publish(event):
            order.append(f"publish:{event.data['record_id']}:{event.data['result']}")
            return asyncio.create_task(asyncio.sleep(0))

        with patch("channel.manager.load_callable", return_value=executor), patch("event_bus.publish_default", side_effect=publish):
            manager.load_config({"channels": {"a": {
                "enabled": True, "max_workers": 1,
                "module": "unused", "function": "unused",
            }}})
            await manager.submit(ChannelTask("1", "u", "a", {}))
            await manager.submit(ChannelTask("2", "u", "a", {}))
            await manager.wait_for_idle("a")

        self.assertEqual(order, [
            "execute:1", "publish:1:EXECUTE_FAILED",
            "execute:2", "publish:2:UNCHANGED",
        ])


if __name__ == "__main__":
    unittest.main()
