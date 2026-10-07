import asyncio
import unittest
from unittest.mock import patch

from channel import ChannelManager, ChannelTask


class TestChannelManager(unittest.IsolatedAsyncioTestCase):
    async def test_same_channel_is_serial(self):
        manager = ChannelManager()
        running = 0
        max_running = 0
        order = []

        async def executor(task):
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            order.append(f"start:{task.record_id}")
            await asyncio.sleep(0.01)
            order.append(f"end:{task.record_id}")
            running -= 1

        with patch("channel.manager.load_callable", return_value=executor):
            manager.load_config({
                "channels": {
                    "a": {
                        "enabled": True,
                        "module": "unused",
                        "function": "unused",
                    }
                }
            })

        await manager.submit(ChannelTask("1", "u", "a", {}))
        await manager.submit(ChannelTask("2", "u", "a", {}))
        await manager.wait_for_idle("a")

        self.assertEqual(max_running, 1)
        self.assertEqual(order, ["start:1", "end:1", "start:2", "end:2"])

    async def test_different_channels_can_run_in_parallel(self):
        manager = ChannelManager()
        started = asyncio.Event()
        release = asyncio.Event()
        active = 0
        max_active = 0

        async def executor(task):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            started.set()
            await release.wait()
            active -= 1

        with patch("channel.manager.load_callable", return_value=executor):
            manager.load_config({
                "channels": {
                    "a": {"enabled": True, "module": "unused", "function": "unused"},
                    "b": {"enabled": True, "module": "unused", "function": "unused"},
                }
            })

        await manager.submit(ChannelTask("1", "u", "a", {}))
        await manager.submit(ChannelTask("2", "u", "b", {}))
        await asyncio.sleep(0.02)

        self.assertEqual(max_active, 2)
        release.set()
        await manager.wait_for_idle("a")
        await manager.wait_for_idle("b")


if __name__ == "__main__":
    unittest.main()
