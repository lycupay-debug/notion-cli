import unittest

from event_bus import Event, EventBus, EventDispatcher


class TestEventBus(unittest.IsolatedAsyncioTestCase):
    async def test_event_bus_only_moves_events(self):
        bus = EventBus()
        event = Event("NEW_TASK", {"record_id": "test-001"})

        await bus.publish(event)

        self.assertEqual(bus.qsize(), 1)
        received = await bus.next_event()

        self.assertIs(received, event)
        self.assertEqual(bus.qsize(), 0)

        bus.task_done()

    async def test_dispatcher_routes_event_directly_to_registered_handler(self):
        dispatcher = EventDispatcher()
        received = []

        async def handle_new_task(event: Event) -> None:
            received.append(event)

        dispatcher.register("NEW_TASK", handle_new_task)

        event = Event("NEW_TASK", {"record_id": "test-002"})
        await dispatcher.dispatch(event)

        self.assertEqual(received, [event])

    async def test_dispatcher_can_route_different_events_independently(self):
        dispatcher = EventDispatcher()
        received = []

        async def handle_a(event: Event) -> None:
            received.append(("A", event.event_id))

        async def handle_b(event: Event) -> None:
            received.append(("B", event.event_id))

        dispatcher.register("EVENT_A", handle_a)
        dispatcher.register("EVENT_B", handle_b)

        event_a = Event("EVENT_A")
        event_b = Event("EVENT_B")

        await dispatcher.dispatch(event_b)
        await dispatcher.dispatch(event_a)

        self.assertEqual(
            received,
            [
                ("B", event_b.event_id),
                ("A", event_a.event_id),
            ],
        )

    async def test_bus_and_dispatcher_work_together(self):
        bus = EventBus()
        dispatcher = EventDispatcher()
        received = []

        async def handle_new_task(event: Event) -> None:
            received.append(event.data["record_id"])

        dispatcher.register("NEW_TASK", handle_new_task)

        await bus.publish(Event("NEW_TASK", {"record_id": "A"}))
        await bus.publish(Event("NEW_TASK", {"record_id": "B"}))

        await dispatcher.dispatch(await bus.next_event())
        bus.task_done()

        await dispatcher.dispatch(await bus.next_event())
        bus.task_done()

        self.assertEqual(received, ["A", "B"])

    async def test_dispatcher_raises_for_unknown_event_type(self):
        dispatcher = EventDispatcher()

        with self.assertRaisesRegex(LookupError, "UNKNOWN"):
            await dispatcher.dispatch(Event("UNKNOWN"))

    def test_event_serialization_contains_standard_fields(self):
        event = Event("NEW_TASK", {"record_id": "test-003"})
        payload = event.to_dict()

        self.assertEqual(payload["event_id"], event.event_id)
        self.assertEqual(payload["event_type"], "NEW_TASK")
        self.assertEqual(payload["data"]["record_id"], "test-003")
        self.assertTrue(payload["created_at"])


if __name__ == "__main__":
    unittest.main()
