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
