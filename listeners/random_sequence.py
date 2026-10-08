from __future__ import annotations

import asyncio
import random

from core.logger import error, info
from notion.pages import retrieve_page, update_page


SEQUENCE_PROPERTY = "序号"


def _read_rich_text(prop: dict) -> str:
    return "".join(
        item.get("plain_text", "")
        for item in prop.get("rich_text", [])
    )


class RandomSequenceListener:
    """为指定数据源的「序号」字段生成随机 4 位数字。"""

    def handle(self, page_id: str):
        info(f"[RandomSequenceListener] START page_id={page_id}")

        page = retrieve_page(page_id)
        properties = page.get("properties") or {}
        prop = properties.get(SEQUENCE_PROPERTY)

        if not isinstance(prop, dict):
            raise RuntimeError(
                f"页面缺少「{SEQUENCE_PROPERTY}」字段：page_id={page_id}"
            )

        current_value = _read_rich_text(prop)
        info(
            f"[RandomSequenceListener] CURRENT_VALUE "
            f"page_id={page_id} value={current_value!r}"
        )

        # 幂等保护：已经是合法 4 位数字时不再写入。
        if len(current_value) == 4 and current_value.isdigit():
            info(
                f"[RandomSequenceListener] UNCHANGED "
                f"page_id={page_id} value={current_value}"
            )
            return {
                "status": "UNCHANGED",
                "page_id": page_id,
                "value": current_value,
            }

        value = f"{random.randint(0, 9999):04d}"
        info(
            f"[RandomSequenceListener] UPDATE_START "
            f"page_id={page_id} value={value}"
        )

        update_page(
            page_id,
            {
                SEQUENCE_PROPERTY: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": value},
                        }
                    ]
                }
            },
        )

        updated_page = retrieve_page(page_id)
        updated_prop = (updated_page.get("properties") or {}).get(
            SEQUENCE_PROPERTY
        )
        actual_value = _read_rich_text(updated_prop or {})

        info(
            f"[RandomSequenceListener] VERIFY_VALUE "
            f"page_id={page_id} value={actual_value!r}"
        )

        if actual_value != value:
            error(
                f"[RandomSequenceListener] VERIFY_FAILED "
                f"page_id={page_id} actual={actual_value!r} "
                f"expected={value!r}"
            )
            return {
                "status": "FAILED",
                "page_id": page_id,
                "value": value,
                "actual_value": actual_value,
                "verified": False,
            }

        info(
            f"[RandomSequenceListener] SUCCESS "
            f"page_id={page_id} value={value}"
        )
        return {
            "status": "UPDATED",
            "page_id": page_id,
            "value": value,
            "verified": True,
        }


async def execute_random_sequence(task):
    record_id = getattr(task, "record_id", None)
    if not record_id:
        raise ValueError("random_sequence task is missing record_id")

    info(f"[RandomSequenceChannel] START record_id={record_id}")

    from methods.get_task_path import get_task_path
    from methods.read_json_file import read_json_file

    task_path = get_task_path(record_id)
    task_data = read_json_file(task_path)

    if not isinstance(task_data, dict):
        raise ValueError(f"task is not an object: {record_id}")

    entity = task_data.get("entity") or {}
    page_id = entity.get("id")
    if not page_id:
        raise ValueError(f"task is missing entity.id: {record_id}")

    info(
        f"[RandomSequenceChannel] ENTITY_RESOLVED "
        f"record_id={record_id} page_id={page_id}"
    )

    try:
        result = await asyncio.to_thread(
            RandomSequenceListener().handle,
            page_id,
        )
    except Exception as exc:
        error(
            f"[RandomSequenceChannel] FAILED "
            f"record_id={record_id} page_id={page_id} "
            f"error={type(exc).__name__}: {exc}"
        )
        raise

    info(
        f"[RandomSequenceChannel] DONE "
        f"record_id={record_id} result={result!r}"
    )
    return result
