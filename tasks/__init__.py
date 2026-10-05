"""
Task Layer

统一管理所有需要执行的任务。

任务层不区分：
- 主线任务
- 后台任务
- Listener 任务
- 手动任务
- 自动任务

所有任务统一进入 tasks.json。
"""

from .manager import TaskManager

__all__ = [
    "TaskManager",
]