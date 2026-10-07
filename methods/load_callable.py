from __future__ import annotations

import importlib
from collections.abc import Callable


def load_callable(module_name: str, function_name: str) -> Callable:
    """从模块路径动态加载一个可调用对象。"""
    if not module_name:
        raise ValueError("module_name cannot be empty")
    if not function_name:
        raise ValueError("function_name cannot be empty")

    module = importlib.import_module(module_name)

    try:
        handler = getattr(module, function_name)
    except AttributeError as exc:
        raise AttributeError(
            f"callable not found: {module_name}.{function_name}"
        ) from exc

    if not callable(handler):
        raise TypeError(
            f"configured object is not callable: "
            f"{module_name}.{function_name}"
        )

    return handler
