from notion_client import APIErrorCode, APIResponseError

from notion.pages import retrieve_page, update_page
from notion.databases import retrieve_database


class SystemLedgerListener:

    def handle(self, page_id):
        print(
            f"[SystemLedgerListener] "
            f"开始处理 page_id: {page_id}"
        )

        # ========================================================
        # 1. 获取当前系统结构总账页面
        # ========================================================

        page = retrieve_page(page_id)

        # ========================================================
        # 2. 获取「数据源链接和快捷链接」
        # ========================================================

        source_prop = page["properties"][
            "数据源链接和快捷链接"
        ]

        # ========================================================
        # 3. 从字段中提取 Notion URL
        # ========================================================

        url = self.extract_notion_url(source_prop)

        if not url:
            raise RuntimeError(
                "「数据源链接和快捷链接」中没有找到 Notion URL"
            )

        print(
            f"[SystemLedgerListener] "
            f"目标 URL: {url}"
        )

        # ========================================================
        # 4. 从 URL 提取原始 Notion ID
        # ========================================================

        raw_id = self.extract_notion_id(url)

        print(
            f"[SystemLedgerListener] "
            f"原始 Notion ID: {raw_id}"
        )

        # ========================================================
        # 5. 判断对象类型
        #
        # Page:
        #     target_id = Page ID
        #
        # Database:
        #     target_id = Data Source ID
        #
        # Error:
        #     target_id = "错误"
        # ========================================================

        resolved = self.resolve_object(raw_id)

        print(
            f"[SystemLedgerListener] "
            f"对象类型: {resolved['status']}"
        )

        target_id = resolved["target_id"]

        print(
            f"[SystemLedgerListener] "
            f"最终写入 ID: {target_id}"
        )

        # ========================================================
        # 6. 读取当前「Notion页面ID」
        # ========================================================

        current_prop = page["properties"][
            "Notion页面ID"
        ]

        current_value = self.extract_rich_text(
            current_prop
        )

        print(
            f"[SystemLedgerListener] "
            f"当前 Notion页面ID: {current_value}"
        )

        # ========================================================
        # 7. 判断是否已经正确
        # ========================================================

        if current_value == target_id:
            print(
                "[SystemLedgerListener] "
                "当前值已经正确，无需写入。"
            )

            return {
                "status": "UNCHANGED",
                "page_id": page_id,
                "raw_id": raw_id,
                "object_type": resolved["status"],
                "target_id": target_id,
            }

        # ========================================================
        # 8. 写入「Notion页面ID」
        # ========================================================

        update_page(
            page_id,
            {
                "Notion页面ID": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": target_id
                            }
                        }
                    ]
                }
            }
        )

        print(
            "[SystemLedgerListener] "
            f"已写入 Notion页面ID: {target_id}"
        )

        # ========================================================
        # 9. 回读验证
        # ========================================================

        updated_page = retrieve_page(page_id)

        updated_prop = updated_page["properties"][
            "Notion页面ID"
        ]

        updated_value = self.extract_rich_text(
            updated_prop
        )

        # ========================================================
        # 10. 验证失败
        # ========================================================

        if updated_value != target_id:
            raise RuntimeError(
                f"回读验证失败："
                f"实际值={updated_value!r}，"
                f"期望值={target_id!r}"
            )

        # ========================================================
        # 11. 验证成功
        # ========================================================

        print(
            "[SystemLedgerListener] "
            "写入 + 回读验证成功"
        )

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
            if error.code != APIErrorCode.ObjectNotFound:
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
    def resolve_object(raw_id):
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
            if error.code != APIErrorCode.ObjectNotFound:
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

    # ============================================================
    # URL 提取
    # ============================================================

    @staticmethod
    def extract_notion_url(prop):
        """
        从 Notion 属性中提取 URL。

        支持：
        1. rich_text.href
        2. rich_text.text.link.url
        3. plain_text 中直接存在 Notion URL
        """

        for item in prop.get("rich_text", []):

            # ----------------------------------------------------
            # 方式 1：href
            # ----------------------------------------------------

            if item.get("href"):
                return item["href"]

            # ----------------------------------------------------
            # 方式 2：text.link.url
            # ----------------------------------------------------

            text = item.get(
                "text",
                {}
            )

            link = text.get("link")

            if link and link.get("url"):
                return link["url"]

            # ----------------------------------------------------
            # 方式 3：plain_text
            # ----------------------------------------------------

            plain_text = item.get(
                "plain_text",
                ""
            )

            if plain_text.startswith(
                "https://app.notion.com/"
            ):
                return plain_text

        return None

    # ============================================================
    # Notion URL → UUID
    # ============================================================

    @staticmethod
    def extract_notion_id(url):
        """
        从 Notion 页面 URL 中提取 UUID。

        支持：

        https://app.notion.com/p/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        以及带查询参数的 URL。
        """

        if not url:
            raise RuntimeError(
                "没有找到 Notion URL"
            )

        marker = "/p/"

        if marker not in url:
            raise RuntimeError(
                f"不是支持的 Notion URL：{url}"
            )

        raw_id = (
            url
            .split(marker, 1)[1]
            .split("?", 1)[0]
            .replace("-", "")
            .replace(" ", "")
        )

        if len(raw_id) != 32:
            raise RuntimeError(
                f"Notion ID 长度异常：{raw_id}"
            )

        return (
            f"{raw_id[:8]}-"
            f"{raw_id[8:12]}-"
            f"{raw_id[12:16]}-"
            f"{raw_id[16:20]}-"
            f"{raw_id[20:]}"
        )

    # ============================================================
    # Rich Text → 普通文本
    # ============================================================

    @staticmethod
    def extract_rich_text(prop):
        return "".join(
            item.get(
                "plain_text",
                ""
            )
            for item in prop.get(
                "rich_text",
                []
            )
        )