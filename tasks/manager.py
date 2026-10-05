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
    7. 已完成/已失败任务保留在 JSON 中，不删除
    8. 同一业务任务（任务名 + 页面 + 属性）只允许存在一个任务实例
    9. 同名但不同业务目标的任务严格串行：前一个终态后，后一个才允许执行
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

    ACTIVE_STATUSES = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_WAITING,
    }

    TERMINAL_STATUSES = {
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
        self.store = store or JSONStore(base_dir=self.task_file.parent.parent)
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
        return max(numbers) + 1 if numbers else 1

    @staticmethod
    def _format_task_key(task_no):
        return f"{task_no:06d}"

    @staticmethod
    def _same_business(task, task_name, target_page_id, target_property):
        return (
            task.get("task") == task_name
            and task.get("target_page_id") == target_page_id
            and task.get("target_property") == target_property
        )

    def _find_existing_business_task(
        self,
        tasks,
        task_name,
        target_page_id,
        target_property,
    ):
        """
        查找同一业务目标的历史任务。

        无论历史任务是 PENDING/RUNNING/WAITING/COMPLETED/FAILED，
        都视为同一业务任务，禁止再次创建。
        """
        matches = [
            task
            for task in tasks.values()
            if self._same_business(
                task,
                task_name,
                target_page_id,
                target_property,
            )
        ]
        if not matches:
            return None

        return min(matches, key=lambda item: item.get("task_no", 0))

    def _has_earlier_same_name_active_task(self, tasks, task_name, task_no):
        """
        同名任务串行规则：

        只要存在更早的同名任务处于 ACTIVE 状态，
        新任务必须 WAITING。
        """
        for other in tasks.values():
            if other.get("task_no", 0) >= task_no:
                continue
            if other.get("task") != task_name:
                continue
            if other.get("status") in self.ACTIVE_STATUSES:
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
        创建任务，并在创建阶段完成两层去重/串行控制：

        1. 同一业务目标已有历史任务：直接返回历史任务，不重复执行。
        2. 同名但不同业务目标存在更早活动任务：新任务创建为 WAITING。
        """
        data = self._load()
        tasks = data.setdefault("tasks", {})

        existing = self._find_existing_business_task(
            tasks,
            task,
            target_page_id,
            target_property,
        )
        if existing is not None:
            return existing

        task_no = self._next_task_no(data)
        task_id = str(uuid4())
        task_key = self._format_task_key(task_no)

        initial_status = self.STATUS_WAITING if (
            self._has_earlier_same_name_active_task(
                tasks,
                task,
                task_no,
            )
        ) else self.STATUS_PENDING

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
        return data.get("tasks", {}).get(self._format_task_key(task_no))

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

        allowed = self.ALLOWED_TRANSITIONS.get(current_status, set())
        if status not in allowed:
            raise ValueError(
                f"Invalid task transition: {current_status} -> {status}"
            )

        task["status"] = status
        if result is not None:
            task["result"] = result

        self._save(data)
        return task

    def release_waiting_tasks(self):
        """
        释放已经等到前置同名任务终态的 WAITING 任务。

        前置任务 COMPLETED 或 FAILED 都代表前置任务已经执行结束。
        FAILED 不会被重试，但不会永久阻塞后续独立业务目标。
        """
        data = self._load()
        tasks = data.get("tasks", {})
        changed = False

        ordered = sorted(
            tasks.values(),
            key=lambda item: item.get("task_no", 0),
        )

        for task in ordered:
            if task.get("status") != self.STATUS_WAITING:
                continue

            task_no = task.get("task_no", 0)
            task_name = task.get("task")

            blocked = False
            for other in ordered:
                if other.get("task_no", 0) >= task_no:
                    continue
                if other.get("task") != task_name:
                    continue
                if other.get("status") in self.ACTIVE_STATUSES:
                    blocked = True
                    break

            if not blocked:
                task["status"] = self.STATUS_PENDING
                changed = True

        if changed:
            self._save(data)

        return [
            task
            for task in ordered
            if task.get("status") == self.STATUS_PENDING
        ]

    def get_next_pending_task(self):
        """
        获取 task_no 最小的 PENDING 任务。

        每次调用前先释放已经完成前置依赖的 WAITING 任务。
        """
        self.release_waiting_tasks()
        tasks = self.list_tasks()

        for task in tasks:
            if task.get("status") == self.STATUS_PENDING:
                return task
        return None

    def has_conflict(self, task):
        page_id = task.get("target_page_id")
        target_property = task.get("target_property")

        if not page_id or not target_property:
            return False

        current_task_id = task.get("task_id")

        for other in self.list_tasks():
            if other.get("task_id") == current_task_id:
                continue
            if other.get("target_page_id") != page_id:
                continue
            if other.get("target_property") != target_property:
                continue
            if other.get("status") in self.ACTIVE_STATUSES:
                if other.get("task_no", 0) < task.get("task_no", 0):
                    return True

        return False

    def mark_waiting_if_conflict(self, task):
        if not self.has_conflict(task):
            return False

        if task.get("status") != self.STATUS_WAITING:
            self.update_status(
                task["task_no"],
                self.STATUS_WAITING,
            )
        return True
