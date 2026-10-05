from pathlib import Path

from notion.search import search

from core.json_store import JSONStore

from .dispatcher import Dispatcher
from .identity_service import ObjectIdentityService


STATE_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "global_state.json"
)


class GlobalWatcher:
    """
    全局 Notion 页面状态监视器。

    职责：
    1. 获取 Page ID / last_edited_time / URL
    2. 与本地 JSON 比较
    3. 判断 NEW / CHANGED / UNCHANGED
    4. NEW 页面自动建立对象身份
    5. 将 NEW / CHANGED 的 page_id 传递给 Dispatcher

    JSON 数据访问统一通过 JSONStore。

    不负责：
    - 执行具体业务 Listener
    - 修改 Notion 页面内容
    """

    def __init__(self):
        self.store = JSONStore()

        self.identity_service = ObjectIdentityService()
        self.dispatcher = Dispatcher()

        self.state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        # IdentityService 仍然使用当前 state。
        # Dispatcher 每次 dispatch 都从磁盘读取最新状态，
        # 因此不再向 Dispatcher 注入共享内存 state。
        self.identity_service.state = self.state

    def check(self):

        # ==================================================
        # 每一轮开始时重新读取最新 JSON
        # ==================================================

        self.state = self.store.load(
            STATE_FILE,
            default={
                "pages": {}
            },
        )

        self.identity_service.state = self.state

        # Search 本身采用分页；这里必须完整读取，不能只监视前 100 个页面。
        current_pages = []
        cursor = None

        while True:
            search_response = search(
                object_type="page",
                start_cursor=cursor,
                page_size=100,
            )

            current_pages.extend(
                {
                    "id": page["id"],
                    "last_edited_time": page["last_edited_time"],
                    "url": page["url"],
                }
                for page in search_response.get("results", [])
            )

            if not search_response.get("has_more"):
                break

            cursor = search_response.get("next_cursor")
            if not cursor:
                raise RuntimeError(
                    "Notion Search 分页返回 has_more=true，但 next_cursor 为空"
                )

        pages_state = self.state.setdefault(
            "pages",
            {},
        )

        changes = []

        for page in current_pages:

            page_id = page["id"]
            current_time = page["last_edited_time"]
            current_url = page["url"]

            old = pages_state.get(page_id)

            if old is None:
                status = "NEW"

            elif old.get("last_edited_time") != current_time:
                status = "CHANGED"

            else:
                status = "UNCHANGED"

            change = {
                "status": status,
                "id": page_id,
                "last_edited_time": current_time,
                "url": current_url,
            }

            # ==================================================
            # NEW
            # ==================================================

            if status == "NEW":

                pages_state[page_id] = {
                    "last_edited_time": current_time,
                    "url": current_url,
                    "object": None,
                }

                # 保存基础页面状态
                self.store.save(
                    STATE_FILE,
                    self.state,
                )

                # 自动识别对象身份
                identity_result = (
                    self.identity_service.check_page(page_id)
                )

                change["identity"] = identity_result

                # IdentityService 已经重新读取并写入 JSON。
                # 重新读取，确保 Dispatcher 后续读取到最新磁盘状态。
                self.state = self.store.load(
                    STATE_FILE,
                    default={
                        "pages": {}
                    },
                )

                self.identity_service.state = self.state

                pages_state = self.state.setdefault(
                    "pages",
                    {},
                )

                # 身份识别完成后进行 Dispatcher 路由。
                route_result = self.dispatcher.dispatch(
                    page_id
                )

                change["route"] = route_result

            # ==================================================
            # CHANGED
            # ==================================================

            elif status == "CHANGED":

                # 页面发生变化后，不能继续使用旧 object。
                # 先重新向 Notion 确认当前 parent / data_source 身份。
                # 如果身份读取失败，则不更新本地时间戳，也不路由任务；
                # 下一轮会继续重试，避免使用陈旧身份写入错误的数据源。
                identity_result = (
                    self.identity_service.check_page(
                        page_id,
                        force=True,
                    )
                )

                change["identity"] = identity_result

                if identity_result.get("status") == "ERROR":
                    changes.append(change)
                    continue

                # 身份确认成功后，才提交本轮页面状态。
                self.state = self.store.load(
                    STATE_FILE,
                    default={
                        "pages": {}
                    },
                )

                self.identity_service.state = self.state

                pages_state = self.state.setdefault(
                    "pages",
                    {}
                )

                current_state = pages_state.setdefault(
                    page_id,
                    {}
                )

                current_state["last_edited_time"] = current_time
                current_state["url"] = current_url

                self.store.save(
                    STATE_FILE,
                    self.state,
                )

                # Dispatcher 自己从磁盘读取最新 state。
                route_result = self.dispatcher.dispatch(
                    page_id
                )

                change["route"] = route_result

            # ==================================================
            # UNCHANGED
            # ==================================================

            else:
                pass

            changes.append(change)

        # ==================================================
        # 最终保存本轮状态
        # ==================================================

        self.store.save(
            STATE_FILE,
            self.state,
        )

        return changes
