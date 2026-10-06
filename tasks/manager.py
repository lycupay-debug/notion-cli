from pathlib import Path
from uuid import uuid4

from core.json_store import JSONStore


TASK_FILE = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "tasks.json"
)


class TaskManager:
    """任务清单管理器。"""

    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_WAITING = "WAITING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED}
    BLOCKING_STATUSES = {STATUS_PENDING, STATUS_RUNNING, STATUS_WAITING}
    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_WAITING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    }

    ALLOWED_TRANSITIONS = {
        STATUS_PENDING: {STATUS_RUNNING, STATUS_WAITING},
        STATUS_WAITING: {STATUS_PENDING},
        STATUS_RUNNING: {STATUS_COMPLETED, STATUS_FAILED},
        STATUS_COMPLETED: set(),
        STATUS_FAILED: set(),
    }

    def __init__(self, task_file=TASK_FILE, store=None):
        self.task_file = Path(task_file)
        self.store = store or JSONStore(base_dir=self.task_file.parent.parent)
        self._ensure_file()

    def _ensure_file(self):
        if not self.task_file.exists():
            self.store.save(self.task_file, {"version": 1, "tasks": {}})

    def _load(self):
        return self.store.reload(self.task_file)

    def _save(self, data):
        return self.store.save(self.task_file, data)

    def _next_task_no(self, data):
        numbers = [
            task.get("task_no")
            for task in data.get("tasks", {}).values()
            if isinstance(task.get("task_no"), int)
        ]
        return max(numbers, default=0) + 1

    @staticmethod
    def _format_task_key(task_no):
        return f"{task_no:06d}"

    def _has_prior_same_name_task(self, tasks, task_name, task_no):
        for existing in tasks.values():
            if existing.get("task_no", 0) >= task_no:
                continue
            if existing.get("task") != task_name:
                continue
            if existing.get("status") in self.BLOCKING_STATUSES:
                return True
        return False

    @staticmethod
    def _same_event(existing, event_key):
        return bool(event_key) and existing.get("event_key") == event_key

    def create_task(
        self,
        task,
        target_page_id=None,
        target_property=None,
        metadata=None,
        event_key=None,
    ):
        """
        创建任务。

        每个真正的新事件创建一个新的 task_no；同一事件被 Watcher
        重复发现时返回原任务，不创建重复任务。
        """
        data = self._load()
        tasks = data.setdefault("tasks", {})

        if event_key:
            for existing in tasks.values():
                if self._same_event(existing, event_key):
                    return existing

        task_no = self._next_task_no(data)
        initial_status = (
            self.STATUS_WAITING
            if self._has_prior_same_name_task(tasks, task, task_no)
            else self.STATUS_PENDING
        )

        task_data = {
            "task_id": str(uuid4()),
            "task_no": task_no,
            "task": task,
            "status": initial_status,
            "target_page_id": target_page_id,
            "target_property": target_property,
            "result": None,
            "metadata": metadata or {},
        }
        if event_key:
            task_data["event_key"] = event_key

        tasks[self._format_task_key(task_no)] = task_data
        self._save(data)
        return task_data

    def get_task(self, task_no):
        return self._load().get("tasks", {}).get(self._format_task_key(task_no))

    def get_task_by_id(self, task_id):
        for task in self._load().get("tasks", {}).values():
            if task.get("task_id") == task_id:
                return task
        return None

    def list_tasks(self):
        tasks = list(self._load().get("tasks", {}).values())
        tasks.sort(key=lambda item: item.get("task_no", 0))
        return tasks

    def update_status(self, task_no, status, result=None):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid task status: {status}")

        data = self._load()
        task = data.get("tasks", {}).get(self._format_task_key(task_no))
        if task is None:
            raise KeyError(f"Task not found: {task_no}")

        current_status = task.get("status")
        if current_status == status:
            if result is not None:
                task["result"] = result
                self._save(data)
            return task

        if status not in self.ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ValueError(f"Invalid task transition: {current_status} -> {status}")

        task["status"] = status
        if result is not None:
            task["result"] = result
        self._save(data)
        return task

    def get_next_pending_task(self):
        for task in self.list_tasks():
            if task.get("status") == self.STATUS_PENDING:
                return task
        return None

    def has_conflict(self, task):
        task_name = task.get("task")
        current_task_no = task.get("task_no", 0)
        if not task_name:
            return False

        for other in self.list_tasks():
            if other.get("task_no", 0) >= current_task_no:
                continue
            if other.get("task") == task_name and other.get("status") in self.BLOCKING_STATUSES:
                return True
        return False

    def mark_waiting_if_conflict(self, task):
        if not self.has_conflict(task):
            return False
        if task.get("status") == self.STATUS_PENDING:
            self.update_status(task["task_no"], self.STATUS_WAITING)
        return True
