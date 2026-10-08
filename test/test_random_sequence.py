import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from listeners.random_sequence import RandomSequenceListener


def test_existing_four_digit_value_is_unchanged():
    page = {
        "properties": {
            "序号": {
                "rich_text": [
                    {"plain_text": "1234"}
                ]
            }
        }
    }

    with patch("listeners.random_sequence.retrieve_page", return_value=page),          patch("listeners.random_sequence.update_page") as update:
        result = RandomSequenceListener().handle("page-id")

    assert result["status"] == "UNCHANGED"
    assert result["value"] == "1234"
    update.assert_not_called()


def test_invalid_value_is_replaced_with_four_digits():
    page = {
        "properties": {
            "序号": {
                "rich_text": [
                    {"plain_text": "abc"}
                ]
            }
        }
    }

    updated_page = {
        "properties": {
            "序号": {
                "rich_text": [
                    {"plain_text": "5678"}
                ]
            }
        }
    }

    with patch(
        "listeners.random_sequence.retrieve_page",
        side_effect=[page, updated_page],
    ), patch("listeners.random_sequence.random.randint", return_value=5678), \
         patch("listeners.random_sequence.update_page") as update:
        result = RandomSequenceListener().handle("page-id")

    assert result["status"] == "UPDATED"
    assert result["value"] == "5678"
    update.assert_called_once()
