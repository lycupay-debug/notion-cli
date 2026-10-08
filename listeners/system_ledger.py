import asyncio

from core.logger import error, info
from notion_client import APIErrorCode, APIResponseError
from notion.pages import retrieve_page, update_page
from notion.databases import retrieve_database

class SystemLedgerListener:
    def handle(self, page_id):
        info(f"[SystemLedgerListener] START page_id={page_id}")
        page = retrieve_page(page_id)
        info(f"[SystemLedgerListener] PAGE_RETRIEVED page_id={page_id}")
        source_prop = page["properties"]["数据源链接和快捷链接"]
        url = self.extract_notion_url(source_prop)
        if not url:
            raise RuntimeError("「数据源链接和快捷链接」中没有找到 Notion URL")
        info(f"[SystemLedgerListener] TARGET_URL page_id={page_id} url={url}")
        raw_id = self.extract_notion_id(url)
        info(f"[SystemLedgerListener] RAW_ID page_id={page_id} raw_id={raw_id}")
        resolved = self.resolve_object(raw_id)
        info(f"[SystemLedgerListener] RESOLVED page_id={page_id} status={resolved['status']} target_id={resolved.get('target_id')}")
        if resolved["status"] == "ERROR":
            raise RuntimeError("无法解析目标 Notion 对象：" f"{resolved.get('reason', 'UNKNOWN')}")
        target_id = resolved["target_id"]
        current_prop = page["properties"]["Notion页面ID"]
        current_value = self.extract_rich_text(current_prop)
        info(f"[SystemLedgerListener] CURRENT_VALUE page_id={page_id} value={current_value}")
        if current_value == target_id:
            info(f"[SystemLedgerListener] UNCHANGED page_id={page_id} target_id={target_id}")
            return {"status": "UNCHANGED", "page_id": page_id, "raw_id": raw_id, "object_type": resolved["status"], "target_id": target_id}
        info(f"[SystemLedgerListener] UPDATE_START page_id={page_id} target_id={target_id}")
        update_page(page_id, {"Notion页面ID": {"rich_text": [{"type": "text", "text": {"content": target_id}}]}})
        info(f"[SystemLedgerListener] UPDATE_DONE page_id={page_id} target_id={target_id}")
        updated_page = retrieve_page(page_id)
        info(f"[SystemLedgerListener] VERIFY_RETRIEVED page_id={page_id}")
        updated_prop = updated_page["properties"]["Notion页面ID"]
        updated_value = self.extract_rich_text(updated_prop)
        info(f"[SystemLedgerListener] VERIFY_VALUE page_id={page_id} value={updated_value}")
        if updated_value != target_id:
            error(f"[SystemLedgerListener] VERIFY_FAILED page_id={page_id} actual={updated_value!r} expected={target_id!r}")
            raise RuntimeError(f"回读验证失败：实际值={updated_value!r}，期望值={target_id!r}")
        info(f"[SystemLedgerListener] SUCCESS page_id={page_id} target_id={target_id}")
        return {"status": "UPDATED", "page_id": page_id, "raw_id": raw_id, "object_type": resolved["status"], "target_id": target_id, "verified": True}

    @staticmethod
    def resolve_object(raw_id):
        info(f"[SystemLedgerListener] RESOLVE_START raw_id={raw_id}")
        try:
            page = retrieve_page(raw_id)
            info(f"[SystemLedgerListener] RESOLVE_PAGE raw_id={raw_id}")
            return {"status": "PAGE", "raw_id": raw_id, "target_id": raw_id, "object": page.get("object"), "parent": page.get("parent")}
        except APIResponseError as exc:
            info(f"[SystemLedgerListener] RESOLVE_PAGE_FAILED raw_id={raw_id} code={exc.code}")
            if exc.code not in (APIErrorCode.ObjectNotFound, APIErrorCode.ValidationError):
                raise
        info(f"[SystemLedgerListener] RESOLVE_DATABASE_START raw_id={raw_id}")
        try:
            database = retrieve_database(raw_id)
        except APIResponseError as exc:
            error(f"[SystemLedgerListener] RESOLVE_DATABASE_FAILED raw_id={raw_id} code={exc.code}")
            if exc.code == APIErrorCode.ObjectNotFound:
                return {"status": "ERROR", "raw_id": raw_id, "target_id": "错误", "reason": "OBJECT_NOT_FOUND", "error_type": type(exc).__name__, "error": str(exc)}
            raise
        data_sources = database.get("data_sources", [])
        info(f"[SystemLedgerListener] DATA_SOURCES raw_id={raw_id} count={len(data_sources)}")
        if not data_sources:
            return {"status": "ERROR", "raw_id": raw_id, "target_id": "错误", "reason": "DATABASE_HAS_NO_DATA_SOURCE"}
        data_source_id = data_sources[0].get("id")
        if not data_source_id:
            return {"status": "ERROR", "raw_id": raw_id, "target_id": "错误", "reason": "DATA_SOURCE_ID_MISSING"}
        info(f"[SystemLedgerListener] RESOLVE_DATABASE_DONE raw_id={raw_id} data_source_id={data_source_id}")
        return {"status": "DATABASE", "raw_id": raw_id, "target_id": data_source_id, "object": database.get("object"), "data_sources": data_sources}

    @staticmethod
    def extract_notion_url(prop):
        for item in prop.get("rich_text", []):
            if item.get("href"):
                return item["href"]
            text = item.get("text", {})
            link = text.get("link")
            if link and link.get("url"):
                return link["url"]
            plain_text = item.get("plain_text", "")
            if plain_text.startswith("https://app.notion.com/"):
                return plain_text
        return None

    @staticmethod
    def extract_notion_id(url):
        if not url:
            raise RuntimeError("没有找到 Notion URL")
        marker = "/p/"
        if marker not in url:
            raise RuntimeError(f"不是支持的 Notion URL：{url}")
        raw_id = url.split(marker, 1)[1].split("?", 1)[0].replace("-", "").replace(" ", "")
        if len(raw_id) != 32:
            raise RuntimeError(f"Notion ID 长度异常：{raw_id}")
        return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

    @staticmethod
    def extract_rich_text(prop):
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))

async def execute_system_ledger(task):
    record_id = getattr(task, "record_id", None)
    if not record_id:
        raise ValueError("system_ledger task is missing record_id")
    info(f"[SystemLedgerChannel] START record_id={record_id}")
    from methods.get_task_path import get_task_path
    from methods.read_json_file import read_json_file
    task_path = get_task_path(record_id)
    info(f"[SystemLedgerChannel] LOAD_TASK record_id={record_id} path={task_path}")
    task_data = read_json_file(task_path)
    if not isinstance(task_data, dict):
        raise ValueError(f"task is not an object: {record_id}")
    entity = task_data.get("entity") or {}
    page_id = entity.get("id")
    if not page_id:
        raise ValueError(f"task is missing entity.id: {record_id}")
    info(f"[SystemLedgerChannel] ENTITY_RESOLVED record_id={record_id} page_id={page_id}")
    try:
        result = await asyncio.to_thread(SystemLedgerListener().handle, page_id)
    except Exception as exc:
        error(f"[SystemLedgerChannel] FAILED record_id={record_id} page_id={page_id} error={type(exc).__name__}: {exc}")
        raise
    info(f"[SystemLedgerChannel] DONE record_id={record_id} result={result!r}")
    return result
