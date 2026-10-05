from notion_client import APIErrorCode, APIResponseError

from notion.pages import retrieve_page, update_page
from notion.databases import retrieve_database


class SystemLedgerListener:

    def handle(self, page_id):
        print(f"[SystemLedgerListener] 开始处理 page_id: {page_id}")
        page = retrieve_page(page_id)

        source_prop = page["properties"]["数据源链接和快捷链接"]
        url = self.extract_notion_url(source_prop)
        if not url:
            raise RuntimeError("「数据源链接和快捷链接」中没有找到 Notion URL")

        print(f"[SystemLedgerListener] 目标 URL: {url}")
        raw_id = self.extract_notion_id(url)
        print(f"[SystemLedgerListener] 原始 Notion ID: {raw_id}")

        resolved = self.resolve_object(raw_id)
        print(f"[SystemLedgerListener] 对象类型: {resolved['status']}")

        if resolved["status"] == "ERROR":
            raise RuntimeError(
                "无法解析目标 Notion 对象："
                f"{resolved.get('reason', 'UNKNOWN')}"
            )

        target_id = resolved["target_id"]
        print(f"[SystemLedgerListener] 最终写入 ID: {target_id}")

        current_prop = page["properties"]["Notion页面ID"]
        current_value = self.extract_rich_text(current_prop)
        print(f"[SystemLedgerListener] 当前 Notion页面ID: {current_value}")

        if current_value == target_id:
            print("[SystemLedgerListener] 当前值已经正确，无需写入。")
            return {
                "status": "UNCHANGED",
                "page_id": page_id,
                "raw_id": raw_id,
                "object_type": resolved["status"],
                "target_id": target_id,
            }

        update_page(
            page_id,
            {
                "Notion页面ID": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": target_id},
                        }
                    ]
                }
            },
        )

        print(f"[SystemLedgerListener] 已写入 Notion页面ID: {target_id}")

        updated_page = retrieve_page(page_id)
        updated_prop = updated_page["properties"]["Notion页面ID"]
        updated_value = self.extract_rich_text(updated_prop)

        if updated_value != target_id:
            raise RuntimeError(
                f"回读验证失败：实际值={updated_value!r}，期望值={target_id!r}"
            )

        print("[SystemLedgerListener] 写入 + 回读验证成功")
        return {
            "status": "UPDATED",
            "page_id": page_id,
            "raw_id": raw_id,
            "object_type": resolved["status"],
            "target_id": target_id,
            "verified": True,
        }

    @staticmethod
    def resolve_object(raw_id):
        """解析 URL 中的 Notion 对象。

        Page ID：retrieve_page 成功后直接返回。
        Database ID：retrieve_page 会返回 ValidationError（明确提示
        'is a database'），此时必须继续调用 retrieve_database，而不是把
        ValidationError 当成最终失败。
        """
        try:
            page = retrieve_page(raw_id)
            return {
                "status": "PAGE",
                "raw_id": raw_id,
                "target_id": raw_id,
                "object": page.get("object"),
                "parent": page.get("parent"),
            }
        except APIResponseError as error:
            if error.code not in (
                APIErrorCode.ObjectNotFound,
                APIErrorCode.ValidationError,
            ):
                raise

        try:
            database = retrieve_database(raw_id)
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                return {
                    "status": "ERROR",
                    "raw_id": raw_id,
                    "target_id": "错误",
                    "reason": "OBJECT_NOT_FOUND",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            raise

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

        raw_id = (
            url.split(marker, 1)[1]
            .split("?", 1)[0]
            .replace("-", "")
            .replace(" ", "")
        )

        if len(raw_id) != 32:
            raise RuntimeError(f"Notion ID 长度异常：{raw_id}")

        return (
            f"{raw_id[:8]}-"
            f"{raw_id[8:12]}-"
            f"{raw_id[12:16]}-"
            f"{raw_id[16:20]}-"
            f"{raw_id[20:]}"
        )

    @staticmethod
    def extract_rich_text(prop):
        return "".join(
            item.get("plain_text", "")
            for item in prop.get("rich_text", [])
        )
