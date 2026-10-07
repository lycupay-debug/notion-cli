import asyncio
import unittest

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

        manager.load_config({
            "channels": {
                "a": {"enabled": True, "module": "test.test_channel_manager", "function": "unused"}
            }
        })
        state = manager._channels["a"]
        state.executor = executor

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

        manager._channels["a"] = manager._channels["b"] = None
        manager._channels.clear()
        from channel.manager import _ChannelState
        manager._channels["a"] = _ChannelState(asyncio.Queue(), executor)
        manager._channels["b"] = _ChannelState(asyncio.Queue(), executor)

        await manager.submit(ChannelTask("1", "u", "a", {}))
        await manager.submit(ChannelTask("2", "u", "b", {}))
        await asyncio.wait_for(started.wait(), timeout=1)
        await asyncio.sleep(0.01)

        self.assertEqual(max_active, 2)
        release.set()
        await manager.wait_for_idle("a")
        await manager.wait_for_idle("b")


if __name__ == "__main__":
    unittest.main()
