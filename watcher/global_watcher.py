from notion.search import get_global_page_snapshot

from .state import load_state, save_state
from .dispatcher import Dispatcher
from .identity_service import ObjectIdentityService


class GlobalWatcher:
    """
    全局 Notion 页面状态监视器。

    职责：
    1. 获取 Page ID / last_edited_time / URL
    2. 与本地 JSON 比较
    3. 判断 NEW / CHANGED / UNCHANGED
    4. NEW 页面自动建立对象身份
    5. 将 NEW / CHANGED 的 page_id 传递给 Dispatcher

    不负责：
    - 执行具体业务 Listener
    - 修改 Notion 页面内容
    """

    def __init__(self):
        self.state = load_state()

        self.identity_service = ObjectIdentityService()
        self.dispatcher = Dispatcher()

        # 三个服务共用当前 state
        self.identity_service.state = self.state
        self.dispatcher.state = self.state

    def check(self):

        # 每一轮开始时重新读取最新 JSON
        self.state = load_state()

        # 同步给其他服务
        self.identity_service.state = self.state
        self.dispatcher.state = self.state

        current_pages = get_global_page_snapshot()

        pages_state = self.state.setdefault("pages", {})

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
                save_state(self.state)

                # 自动识别对象身份
                identity_result = (
                    self.identity_service.check_page(page_id)
                )

                change["identity"] = identity_result

                # IdentityService 已经重新读取并写入 JSON
                # 所以这里必须重新读取最新 state
                self.state = load_state()

                self.identity_service.state = self.state
                self.dispatcher.state = self.state

                pages_state = self.state.setdefault("pages", {})

                # 身份识别完成后进行 Dispatcher 路由
                route_result = self.dispatcher.dispatch(page_id)

                change["route"] = route_result

            # ==================================================
            # CHANGED
            # ==================================================
            elif status == "CHANGED":

                # 保留原有 object
                object_info = old.get("object")

                pages_state[page_id] = {
                    "last_edited_time": current_time,
                    "url": current_url,
                    "object": object_info,
                }

                # 保存更新时间
                save_state(self.state)

                # Dispatcher 使用当前 state
                self.dispatcher.state = self.state

                route_result = self.dispatcher.dispatch(page_id)

                change["route"] = route_result

            # ==================================================
            # UNCHANGED
            # ==================================================
            else:
                pass

            changes.append(change)

        # 最终保存本轮状态
        save_state(self.state)

        return changes