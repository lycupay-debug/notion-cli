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
    """

    # 1. 尝试 Page
    try:
        get_page(raw_id)

        return {
            "status": "PAGE",
            "raw_id": raw_id,
            "target_id": raw_id,
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
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "raw_id": raw_id,
            "target_id": "错误",
            "reason": type(e).__name__,
            "error": str(e),
        }