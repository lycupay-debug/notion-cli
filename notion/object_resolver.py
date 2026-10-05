from notion.pages import get_page
from notion.databases import get_database


def resolve_notion_id(raw_id):
    """
    根据 Notion 对象 ID 判断对象类型，并返回最终写入 ID。

    Page:
        target_id = Page ID

    Database:
        target_id = Data Source ID

    Error:
        target_id = "错误"

    说明：
    2025-09-03 之后 Database 与 Data Source 是不同对象。
    2026-03-11 继续沿用该模型。
    """

    # 1. 尝试 Page
    try:
        page = get_page(raw_id)

        return {
            "status": "PAGE",
            "raw_id": raw_id,
            "target_id": raw_id,
            "object": page.get("object"),
            "parent": page.get("parent"),
        }

    except Exception:
        pass

    # 2. 尝试 Database
    try:
        database = get_database(raw_id)

        data_sources = database.get("data_sources", [])

        if not data_sources:
            return {
                "status": "ERROR",
                "raw_id": raw_id,
                "target_id": "错误",
                "reason": "DATABASE_HAS_NO_DATA_SOURCE",
            }

        data_source_id = data_sources[0].get("id")

        if not data_source_id:
            return {
                "status": "ERROR",
                "raw_id": raw_id,
                "target_id": "错误",
                "reason": "DATA_SOURCE_ID_MISSING",
            }

        return {
            "status": "DATABASE",
            "raw_id": raw_id,
            "target_id": data_source_id,
            "object": database.get("object"),
            "data_sources": data_sources,
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "raw_id": raw_id,
            "target_id": "错误",
            "reason": type(e).__name__,
            "error": str(e),
        }
