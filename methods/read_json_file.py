from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_json_file(relative_path: str, base_dir: str | Path | None = None) -> Any:
    """
    使用项目根目录作为默认基准读取 JSON 文件。

    调用方必须传入相对路径。
    """
    path = Path(relative_path)

    if path.is_absolute():
        raise ValueError("relative_path must be relative")

    root = Path(base_dir).resolve() if base_dir is not None else PROJECT_ROOT
    file_path = (root / path).resolve()

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)
