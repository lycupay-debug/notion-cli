from parser.worker import ParserWorker


SAMPLE = {
    "record_id": "b10f81f8-ed8f-47d2-889e-04027e9a835d",
    "event_id": "93d6c3c1-deda-445c-addb-a76c9a401cf5",
    "event_type": "page.properties_updated",
    "payload": {
        "authors": [
            {
                "id": "3e1d872b-594c-8152-a31f-00026246ba3c",
                "type": "person",
            }
        ],
        "entity": {
            "id": "3eb7613b-20a9-816a-a6e9-e55fcbc05115",
            "type": "page",
        },
        "data": {
            "parent": {
                "id": "8581c831-f383-4ff2-bc9d-c276531b1004",
                "type": "database",
                "data_source_id": "9c7afd69-cba9-44c3-ae20-ad2886498e96",
            },
            "updated_properties": ["C%5EN%3D"],
        },
    },
}


def test_parser_extracts_event():
    result = ParserWorker().parse(SAMPLE)

    assert result["record_id"] == "b10f81f8-ed8f-47d2-889e-04027e9a835d"
    assert result["assignee"] is None
    assert result["task_completed"] is None
    assert result["incomplete_reason"] == ""
    assert result["event_id"] == "93d6c3c1-deda-445c-addb-a76c9a401cf5"
    assert result["event_type"] == "page.properties_updated"
    assert result["author"]["is_person"] is True
    assert result["author"]["is_bot"] is False
    assert result["entity"]["type"] == "page"
    assert result["parent"]["type"] == "database"
    assert result["parent"]["data_source_id"] == (
        "9c7afd69-cba9-44c3-ae20-ad2886498e96"
    )
    assert result["updated_properties"] == ["C%5EN%3D"]


def test_parser_saves_by_recordid(tmp_path):
    tasks_dir = tmp_path / "config" / "tasks"
    worker = ParserWorker(config_dir=tasks_dir)

    parsed = worker.parse(SAMPLE)
    saved = worker.save_parsed(parsed)

    expected_file = (
        tasks_dir / "b10f81f8-ed8f-47d2-889e-04027e9a835d.json"
    )

    assert saved["record_id"] == "b10f81f8-ed8f-47d2-889e-04027e9a835d"
    assert saved["assignee"] is None
    assert saved["task_completed"] is None
    assert saved["incomplete_reason"] == ""
    assert expected_file.exists()
    assert worker.store.load(expected_file)["record_id"] == (
        "b10f81f8-ed8f-47d2-889e-04027e9a835d"
    )


def test_parse_file_reads_persists_and_creates_history(tmp_path):
    event_dir = tmp_path / "webhook_events"
    tasks_dir = tmp_path / "config" / "tasks"
    history_dir = tmp_path / "config" / "parse_history"
    event_dir.mkdir()

    source_file = (
        event_dir / "b10f81f8-ed8f-47d2-889e-04027e9a835d.json"
    )
    source_file.write_text(
        __import__("json").dumps(SAMPLE, ensure_ascii=False),
        encoding="utf-8",
    )

    worker = ParserWorker(
        event_dir=event_dir,
        config_dir=tasks_dir,
        history_dir=history_dir,
    )

    result = worker.parse_file(source_file)

    assert result["record_id"] == SAMPLE["record_id"]
    assert (
        tasks_dir / f'{SAMPLE["record_id"]}.json'
    ).exists()

    history_file = (
        history_dir / f'{SAMPLE["record_id"]}.json'
    )
    assert history_file.exists()
    assert worker.store.load(history_file) == {
        "task_completed": None,
        "task_action": None,
    }


def test_parser_skips_event_already_in_history(tmp_path):
    event_dir = tmp_path / "webhook_events"
    tasks_dir = tmp_path / "config" / "tasks"
    history_dir = tmp_path / "config" / "parse_history"
    event_dir.mkdir()

    source_file = (
        event_dir / "b10f81f8-ed8f-47d2-889e-04027e9a835d.json"
    )
    source_file.write_text(
        __import__("json").dumps(SAMPLE, ensure_ascii=False),
        encoding="utf-8",
    )

    worker = ParserWorker(
        event_dir=event_dir,
        config_dir=tasks_dir,
        history_dir=history_dir,
    )
    worker.create_history(SAMPLE["record_id"])

    assert worker.is_parsed(SAMPLE["record_id"]) is True
    assert worker.parse_file(source_file) is None
    assert not (
        tasks_dir / f'{SAMPLE["record_id"]}.json'
    ).exists()


def test_parse_pending_events_only_parses_unrecorded_events(tmp_path):
    event_dir = tmp_path / "webhook_events"
    tasks_dir = tmp_path / "config" / "tasks"
    history_dir = tmp_path / "config" / "parse_history"
    event_dir.mkdir()

    first = event_dir / "b10f81f8-ed8f-47d2-889e-04027e9a835d.json"
    first.write_text(
        __import__("json").dumps(SAMPLE, ensure_ascii=False),
        encoding="utf-8",
    )

    second_sample = {
        **SAMPLE,
        "record_id": "another-record-id",
    }
    second = event_dir / "another-record-id.json"
    second.write_text(
        __import__("json").dumps(second_sample, ensure_ascii=False),
        encoding="utf-8",
    )

    worker = ParserWorker(
        event_dir=event_dir,
        config_dir=tasks_dir,
        history_dir=history_dir,
    )
    worker.create_history(SAMPLE["record_id"])

    results = worker.parse_pending_events()

    assert len(results) == 1
    assert results[0]["record_id"] == "another-record-id"
    assert (
        tasks_dir / "another-record-id.json"
    ).exists()
    assert not (
        tasks_dir / f'{SAMPLE["record_id"]}.json'
    ).exists()


def test_parse_history_uses_jsonstore(tmp_path):
    history_dir = tmp_path / "config" / "parse_history"
    worker = ParserWorker(history_dir=history_dir)

    history = worker.create_history("test-record-id")

    assert history == {
        "task_completed": None,
        "task_action": None,
    }
    assert (
        history_dir / "test-record-id.json"
    ).exists()
