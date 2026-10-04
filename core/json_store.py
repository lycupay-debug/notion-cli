import json
from pathlib import Path


class JSONStore:
    """
    统一 JSON 数据访问层。

    职责：
    1. 统一读取 JSON
    2. 自动检测文件是否发生外部修改
    3. 未变化时使用内存缓存
    4. 外部修改后自动重新读取
    5. 统一写入 JSON
    6. 写入后同步更新缓存
    7. 支持主动 reload / invalidate

    JSONStore 不负责任何业务语义。
    """

    def __init__(self, base_dir=None):
        self.base_dir = (
            Path(base_dir).resolve()
            if base_dir is not None
            else Path(__file__).resolve().parent.parent
        )

        # {
        #     "绝对路径": {
        #         "mtime_ns": int,
        #         "data": object,
        #     }
        # }
        self._cache = {}

    def _resolve(self, file_path):
        """
        将相对路径转换为基于项目根目录的绝对路径。
        """
        path = Path(file_path)

        if not path.is_absolute():
            path = self.base_dir / path

        return path.resolve()

    @staticmethod
    def _read_file(path):
        """
        从磁盘读取 JSON。
        """
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load(self, file_path, default=None):
        """
        读取 JSON。

        行为：
        - 文件不存在：
            如果提供 default，返回 default；
            否则抛出 FileNotFoundError。
        - 文件没有变化：
            返回缓存数据。
        - 文件发生变化：
            重新读取并更新缓存。
        """
        path = self._resolve(file_path)

        if not path.exists():
            if default is not None:
                return default

            raise FileNotFoundError(path)

        mtime_ns = path.stat().st_mtime_ns
        key = str(path)

        cached = self._cache.get(key)

        if cached is not None:
            if cached["mtime_ns"] == mtime_ns:
                return cached["data"]

        data = self._read_file(path)

        self._cache[key] = {
            "mtime_ns": mtime_ns,
            "data": data,
        }

        return data

    def reload(self, file_path):
        """
        强制从磁盘重新读取 JSON。

        不使用现有缓存。
        """
        path = self._resolve(file_path)

        if not path.exists():
            raise FileNotFoundError(path)

        data = self._read_file(path)

        self._cache[str(path)] = {
            "mtime_ns": path.stat().st_mtime_ns,
            "data": data,
        }

        return data

    def save(self, file_path, data):
        """
        原子写入 JSON。

        写入流程：
        1. 创建临时文件
        2. 写入 JSON
        3. replace 正式文件
        4. 更新内存缓存

        这样可以避免程序写 JSON 时产生半截文件。
        """
        path = self._resolve(file_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_file = path.with_suffix(
            path.suffix + ".tmp"
        )

        with temp_file.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

        temp_file.replace(path)

        self._cache[str(path)] = {
            "mtime_ns": path.stat().st_mtime_ns,
            "data": data,
        }

        return data

    def set(self, file_path, data):
        """
        save() 的语义别名。

        方便以后统一使用：
            store.set(...)
        """
        return self.save(file_path, data)

    def invalidate(self, file_path=None):
        """
        清除缓存。

        file_path=None：
            清空全部缓存。

        指定 file_path：
            只清除指定 JSON 的缓存。
        """
        if file_path is None:
            self._cache.clear()
            return

        path = self._resolve(file_path)

        self._cache.pop(
            str(path),
            None,
        )