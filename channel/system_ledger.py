from __future__ import annotations

from channel.manager import ChannelTask, ChannelExecutionResult
from listeners.system_ledger import SystemLedgerListener


async def execute(task: ChannelTask) -> ChannelExecutionResult:
    """将 ChannelTask 适配到现有 SystemLedgerListener。

    实际业务逻辑全部由 listeners.system_ledger.SystemLedgerListener.handle
    执行；本函数只负责 Channel 与旧 Listener 之间的参数/结果适配。
    """
    result = SystemLedgerListener().handle(task.record_id)

    return ChannelExecutionResult(
        status=result.get("status", "UNKNOWN"),
        record_id=task.record_id,
        channel=task.channel,
        assignee=task.assignee,
        data=result,
    )
