from notion.pages import get_page_identity

from .state import load_state, save_state


class ObjectIdentityService:
    """
    维护 GlobalWatcher 本地 JSON 中的对象归属信息。

    当前策略：
    - object 已存在：跳过，不调用 API
    - object 为空：调用 get_page_identity()
    - 获取成功：写入 JSON
    """

    def __init__(self):
        self.state = load_state()

    def check_missing(self):
        pages = self.state.get("pages", {})

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

                print(f"[Identity] 已确认：{page_id}")
                print(f"  object: {identity.get('object')}")
                print(f"  parent: {parent}")

            except Exception as e:
                failed += 1

                print(
                    f"[Identity ERROR] "
                    f"{page_id}: {type(e).__name__}: {e}"
                )

        save_state(self.state)

        return {
            "checked": checked,
            "skipped": skipped,
            "failed": failed,
        }

    def check_page(self, page_id):

        # --------------------------------------------------
        # 关键：
        # 每次单页识别前重新读取最新 JSON
        # --------------------------------------------------
        self.state = load_state()

        pages = self.state.setdefault("pages", {})

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

            save_state(self.state)

            print(f"[Identity] 已确认：{page_id}")
            print(f"  object: {identity.get('object')}")
            print(f"  parent: {parent}")

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