from pathlib import Path

from notion.pages import get_page_identity

from core.json_store import JSONStore


STATE_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "global_state.json"
)


class ObjectIdentityService:
    """
    维护 GlobalWatcher 本地 JSON 中的对象归属信息。

    职责：
    - 读取页面状态
    - 判断 object 是否已经存在
    - object 为空时调用 Notion API 识别对象身份
    - 将识别结果写回 JSON

    JSON 数据访问统一通过 JSONStore。

    不负责：
    - 页面监听
    - Dispatcher 路由
    - Listener 执行
    """

    def __init__(self):
        self.store = JSONStore()

        self.state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

    def check_missing(self):
        """
        检查所有尚未识别 object 的页面。

        已有 object：
            跳过

        object 为空：
            调用 Notion API 进行识别
        """

        # 每次批量检查前重新读取最新 JSON
        self.state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        pages = self.state.get(
            "pages",
            {},
        )

        checked = 0
        skipped = 0
        failed = 0

        for page_id, data in pages.items():

            if data.get("object"):
                skipped += 1
                continue

            checked += 1

            try:
                identity = get_page_identity(page_id)

                parent = identity.get("parent")

                data["object"] = {
                    "type": identity.get("object"),
                    "parent": parent,
                }

                print(
                    f"[Identity] 已确认：{page_id}"
                )
                print(
                    f"  object: {identity.get('object')}"
                )
                print(
                    f"  parent: {parent}"
                )

            except Exception as e:
                failed += 1

                print(
                    f"[Identity ERROR] "
                    f"{page_id}: "
                    f"{type(e).__name__}: {e}"
                )

        self.store.save(
            STATE_FILE,
            self.state,
        )

        return {
            "checked": checked,
            "skipped": skipped,
            "failed": failed,
        }

    def check_page(self, page_id):
        """
        检查并识别单个页面的对象身份。
        """

        # --------------------------------------------------
        # 每次单页识别前重新读取最新 JSON
        # --------------------------------------------------

        self.state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        pages = self.state.setdefault(
            "pages",
            {},
        )

        data = pages.get(page_id)

        if data is None:
            return {
                "status": "PAGE_NOT_FOUND",
                "page_id": page_id,
            }

        if data.get("object"):
            return {
                "status": "ALREADY_EXISTS",
                "page_id": page_id,
                "object": data["object"],
            }

        try:
            identity = get_page_identity(page_id)

            parent = identity.get("parent")

            data["object"] = {
                "type": identity.get("object"),
                "parent": parent,
            }

            self.store.save(
                STATE_FILE,
                self.state,
            )

            print(
                f"[Identity] 已确认：{page_id}"
            )
            print(
                f"  object: {identity.get('object')}"
            )
            print(
                f"  parent: {parent}"
            )

            return {
                "status": "IDENTIFIED",
                "page_id": page_id,
                "object": data["object"],
            }

        except Exception as e:

            return {
                "status": "ERROR",
                "page_id": page_id,
                "error_type": type(e).__name__,
                "error": str(e),
            }