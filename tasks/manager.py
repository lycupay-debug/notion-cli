from pathlib import Path
from uuid import uuid4

from core.json_store import JSONStore


TASK_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "tasks.json"
)


class TaskManager:
    """
    任务清单管理器。

    核心原则：

    1. 所有任务统一进入 tasks.json
    2. 不使用内存任务缓存
    3. 每次读取任务时直接从磁盘 reload
    4. task_id 使用 UUID，负责唯一身份
    5. task_no 负责任务顺序
    6. 不使用时间参与任务排序
    7. 已完成任务保留在 JSON 中，不删除
    """

    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_WAITING = "WAITING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_WAITING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    }

    def __init__(
        self,
        task_file=TASK_FILE,
        store=None,
    ):
        self.task_file = Path(task_file)

        self.store = store or JSONStore(
            base_dir=self.task_file.parent.parent
        )

        self._ensure_file()

    # ---------------------------------------------------------
    # 基础 JSON
    # ---------------------------------------------------------

    def _ensure_file(self):
        """
        确保 tasks.json 存在。

        不存在时创建基础结构。
        """
        if not self.task_file.exists():
            self.store.save(
                self.task_file,
                {
                    "version": 1,
                    "tasks": {},
                },
            )

    def _load(self):
        """
        强制从磁盘读取最新任务清单。

        注意：
        这里故意使用 reload()，
        不使用 JSONStore.load()，
        避免任务层依赖 JSONStore 的内存缓存。
        """
        return self.store.reload(self.task_file)

    def _save(self, data):
        """
        写回 tasks.json。
        """
        return self.store.save(
            self.task_file,
            data,
        )

    # ---------------------------------------------------------
    # Task No
    # ---------------------------------------------------------

    def _next_task_no(self, data):
        """
        计算下一个任务编号。

        task_no 不依赖时间。

        已存在：
            1
            2
            5

        下一次：
            6
        """
        tasks = data.get("tasks", {})

        if not tasks:
            return 1

        numbers = []

        for task in tasks.values():
            task_no = task.get("task_no")

            if isinstance(task_no, int):
                numbers.append(task_no)

        if not numbers:
            return 1

        return max(numbers) + 1

    @staticmethod
    def _format_task_key(task_no):
        """
        将任务编号转换成 JSON 中的人类可读键。

        1 -> 000001
        12 -> 000012
        """
        return f"{task_no:06d}"

    # ---------------------------------------------------------
    # 创建任务
    # ---------------------------------------------------------

    def create_task(
        self,
        task,
        target_page_id=None,
        target_property=None,
        metadata=None,
    ):
        """
        创建一个新任务。

        参数：

        task:
            任务名称。

        target_page_id:
            任务目标页面。

        target_property:
            任务目标属性。

        metadata:
            其他任务参数。

        返回：
            创建后的完整任务对象。
        """

        data = self._load()

        tasks = data.setdefault(
            "tasks",
            {},
        )

        task_no = self._next_task_no(data)

        task_id = str(uuid4())

        task_key = self._format_task_key(
            task_no
        )

        task_data = {
            "task_id": task_id,
            "task_no": task_no,
            "task": task,
            "status": self.STATUS_PENDING,
            "target_page_id": target_page_id,
            "target_property": target_property,
            "result": None,
            "metadata": metadata or {},
        }

        tasks[task_key] = task_data

        self._save(data)

        return task_data

    # ---------------------------------------------------------
    # 读取任务
    # ---------------------------------------------------------

    def get_task(self, task_no):
        """
        根据 task_no 获取任务。

        每次都会重新读取磁盘。
        """

        data = self._load()

        task_key = self._format_task_key(
            task_no
        )

        return data.get(
            "tasks",
            {}
        ).get(task_key)

    def get_task_by_id(self, task_id):
        """
        根据 UUID 获取任务。
        """

        data = self._load()

        for task in data.get(
            "tasks",
            {}
        ).values():

            if task.get("task_id") == task_id:
                return task

        return None

    def list_tasks(self):
        """
        获取全部任务。

        返回按照 task_no 排序后的列表。
        """

        data = self._load()

        tasks = list(
            data.get(
                "tasks",
                {}
            ).values()
        )

        tasks.sort(
            key=lambda item: item.get(
                "task_no",
                0,
            )
        )

        return tasks

    # ---------------------------------------------------------
    # 状态
    # ---------------------------------------------------------

    def update_status(
        self,
        task_no,
        status,
        result=None,
    ):
        """
        更新任务状态。

        每次先从磁盘读取，
        修改后再完整写回。

        不允许非法状态。
        """

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid task status: {status}"
            )

        data = self._load()

        task_key = self._format_task_key(
            task_no
        )

        tasks = data.get(
            "tasks",
            {}
        )

        task = tasks.get(task_key)

        if task is None:
            raise KeyError(
                f"Task not found: {task_no}"
            )

        task["status"] = status

        if result is not None:
            task["result"] = result

        self._save(data)

        return task

    # ---------------------------------------------------------
    # 下一任务
    # ---------------------------------------------------------

    def get_next_pending_task(self):
        """
        获取 task_no 最小的 PENDING 任务。

        不改变任务状态。
        """

        tasks = self.list_tasks()

        for task in tasks:
            if (
                task.get("status")
                == self.STATUS_PENDING
            ):
                return task

        return None

    # ---------------------------------------------------------
    # 冲突判断
    # ---------------------------------------------------------

    def has_conflict(
        self,
        task,
    ):
        """
        判断当前任务是否存在目标冲突。

        冲突条件：

            target_page_id 相同
            +
            target_property 相同

        已完成的任务不构成执行冲突。

        当前任务自身不会与自身冲突。
        """

        page_id = task.get(
            "target_page_id"
        )

        target_property = task.get(
            "target_property"
        )

        if not page_id or not target_property:
            return False

        current_task_id = task.get(
            "task_id"
        )

        tasks = self.list_tasks()

        for other in tasks:

            if other.get(
                "task_id"
            ) == current_task_id:
                continue

            if other.get(
                "target_page_id"
            ) != page_id:
                continue

            if other.get(
                "target_property"
            ) != target_property:
                continue

            other_status = other.get(
                "status"
            )

            if other_status in {
                self.STATUS_PENDING,
                self.STATUS_RUNNING,
                self.STATUS_WAITING,
            }:
                if (
                    other.get("task_no", 0)
                    < task.get("task_no", 0)
                ):
                    return True

        return False

    # ---------------------------------------------------------
    # 等待状态
    # ---------------------------------------------------------

    def mark_waiting_if_conflict(
        self,
        task,
    ):
        """
        如果存在更早的同目标任务，
        则将当前任务标记为 WAITING。

        返回：
            True  = 已进入等待
            False = 不需要等待
        """

        if not self.has_conflict(task):
            return False

        if task.get("status") != self.STATUS_WAITING:
            self.update_status(
                task["task_no"],
                self.STATUS_WAITING,
            )

        return True