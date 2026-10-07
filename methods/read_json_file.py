from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_json_file(relative_path: str) -> Any:
    """
    使用项目根目录作为基准读取 JSON 文件。

    调用方必须传入相对路径。
    """
    path = Path(relative_path)

    if path.is_absolute():
        raise ValueError("relative_path must be relative")

    file_path = (PROJECT_ROOT / path).resolve()

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)
