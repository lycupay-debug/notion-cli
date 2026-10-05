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
    2. 每次读取任务时直接从磁盘 reload
    3. task_id 使用 UUID，负责唯一身份
    4. task_no 负责任务顺序和优先级
    5. 不使用时间参与任务排序
    6. 已完成/失败任务保留在 JSON 中，不删除
    7. 每一个事件都创建独立任务，不做业务去重
    8. 同名任务按照 task_no 串行：前一个同名任务未结束时，后一个进入 WAITING
    """

    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_WAITING = "WAITING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    TERMINAL_STATUSES = {
        STATUS_COMPLETED,
        STATUS_FAILED,
    }

    BLOCKING_STATUSES = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_WAITING,
    }

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_WAITING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    }

    ALLOWED_TRANSITIONS = {
        STATUS_PENDING: {
            STATUS_RUNNING,
            STATUS_WAITING,
        },
        STATUS_WAITING: {
            STATUS_PENDING,
        },
        STATUS_RUNNING: {
            STATUS_COMPLETED,
            STATUS_FAILED,
        },
        STATUS_COMPLETED: set(),
        STATUS_FAILED: set(),
    }

    def __init__(self, task_file=TASK_FILE, store=None):
        self.task_file = Path(task_file)
        self.store = store or JSONStore(
            base_dir=self.task_file.parent.parent
        )
        self._ensure_file()

    def _ensure_file(self):
        if not self.task_file.exists():
            self.store.save(
                self.task_file,
                {"version": 1, "tasks": {}},
            )

    def _load(self):
        return self.store.reload(self.task_file)

    def _save(self, data):
        return self.store.save(self.task_file, data)

    def _next_task_no(self, data):
        tasks = data.get("tasks", {})
        if not tasks:
            return 1

        numbers = [
            task.get("task_no")
            for task in tasks.values()
            if isinstance(task.get("task_no"), int)
        ]

        return max(numbers, default=0) + 1

    @staticmethod
    def _format_task_key(task_no):
        return f"{task_no:06d}"

    def _has_prior_same_name_task(self, tasks, task_name, task_no):
        """
        判断当前任务之前是否存在同名、尚未结束的任务。

        注意：
        - 只比较 task 名称和 task_no
        - 不比较 page_id/property
        - COMPLETED/FAILED 都属于已经结束
        """
        for existing in tasks.values():
            if existing.get("task_no", 0) >= task_no:
                continue

            if existing.get("task") != task_name:
                continue

            if existing.get("status") in self.BLOCKING_STATUSES:
                return True

        return False

    def create_task(
        self,
        task,
        target_page_id=None,
        target_property=None,
        metadata=None,
    ):
        """
        创建一个独立的新任务。

        不做业务去重：即使 task/page/property 完全相同，
        每次事件仍然创建新的 task_no。

        同名任务：
            前一个同名任务未结束 -> WAITING
            前一个同名任务已 COMPLETED/FAILED -> PENDING
        """
        data = self._load()
        tasks = data.setdefault("tasks", {})

        task_no = self._next_task_no(data)

        initial_status = self.STATUS_WAITING
        if not self._has_prior_same_name_task(
            tasks,
            task,
            task_no,
        ):
            initial_status = self.STATUS_PENDING

        task_id = str(uuid4())
        task_key = self._format_task_key(task_no)

        task_data = {
            "task_id": task_id,
            "task_no": task_no,
            "task": task,
            "status": initial_status,
            "target_page_id": target_page_id,
            "target_property": target_property,
            "result": None,
            "metadata": metadata or {},
        }

        tasks[task_key] = task_data
        self._save(data)

        return task_data

    def get_task(self, task_no):
        data = self._load()
        return data.get("tasks", {}).get(
            self._format_task_key(task_no)
        )

    def get_task_by_id(self, task_id):
        data = self._load()
        for task in data.get("tasks", {}).values():
            if task.get("task_id") == task_id:
                return task
        return None

    def list_tasks(self):
        data = self._load()
        tasks = list(data.get("tasks", {}).values())
        tasks.sort(key=lambda item: item.get("task_no", 0))
        return tasks

    def update_status(self, task_no, status, result=None):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid task status: {status}")

        data = self._load()
        task_key = self._format_task_key(task_no)
        tasks = data.get("tasks", {})
        task = tasks.get(task_key)

        if task is None:
            raise KeyError(f"Task not found: {task_no}")

        current_status = task.get("status")

        if current_status == status:
            if result is not None:
                task["result"] = result
                self._save(data)
            return task

        allowed = self.ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        )

        if status not in allowed:
            raise ValueError(
                f"Invalid task transition: {current_status} -> {status}"
            )

        task["status"] = status

        if result is not None:
            task["result"] = result

        self._save(data)
        return task

    def get_next_pending_task(self):
        """
        返回 task_no 最小的 PENDING 任务。

        COMPLETED/FAILED 永远不会再次返回。
        WAITING 必须先由 Recovery 转为 PENDING。
        """
        for task in self.list_tasks():
            if task.get("status") == self.STATUS_PENDING:
                return task
        return None

    def has_conflict(self, task):
        """
        判断是否存在更早的同名、未结束任务。

        这是同名任务串行规则，不是业务去重规则。
        """
        task_name = task.get("task")
        current_task_no = task.get("task_no", 0)

        if not task_name:
            return False

        for other in self.list_tasks():
            if other.get("task_no", 0) >= current_task_no:
                continue

            if other.get("task") != task_name:
                continue

            if other.get("status") in self.BLOCKING_STATUSES:
                return True

        return False

    def mark_waiting_if_conflict(self, task):
        if not self.has_conflict(task):
            return False

        if task.get("status") == self.STATUS_PENDING:
            self.update_status(
                task["task_no"],
                self.STATUS_WAITING,
            )

        return True
