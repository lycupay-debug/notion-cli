from pathlib import Path
import json
import tempfile

from core.json_store import JSONStore


def print_section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    print_section("JSONStore 本地功能测试")

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir = Path(temp_dir)

        test_file = temp_dir / "test.json"

        store = JSONStore(base_dir=temp_dir)

        # ==================================================
        # 1. 第一次写入
        # ==================================================

        print_section("1. 测试 save()")

        data_v1 = {
            "version": 1,
            "name": "JSONStore Test",
        }

        store.save(
            test_file,
            data_v1,
        )

        print("写入数据：")
        print(data_v1)

        # ==================================================
        # 2. 第一次读取
        # ==================================================

        print_section("2. 测试第一次 load()")

        result = store.load(
            test_file,
        )

        print("读取结果：")
        print(result)

        assert result == data_v1

        print("PASS")

        # ==================================================
        # 3. 第二次读取
        # ==================================================

        print_section("3. 测试缓存读取")

        result_2 = store.load(
            test_file,
        )

        print("第二次读取结果：")
        print(result_2)

        assert result_2 == data_v1

        print("PASS")

        # ==================================================
        # 4. 模拟外部程序修改 JSON
        # ==================================================

        print_section("4. 测试外部修改检测")

        data_v2 = {
            "version": 2,
            "name": "JSONStore External Update",
        }

        with test_file.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data_v2,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

        print("外部修改后的数据：")
        print(data_v2)

        # ==================================================
        # 5. 再次 load
        # ==================================================

        print_section("5. 测试 mtime_ns 自动检测")

        result_3 = store.load(
            test_file,
        )

        print("JSONStore 读取结果：")
        print(result_3)

        assert result_3 == data_v2

        print("PASS：检测到外部修改并重新读取")

        # ==================================================
        # 6. 测试 save() 后缓存同步
        # ==================================================

        print_section("6. 测试 save() 后缓存同步")

        data_v3 = {
            "version": 3,
            "name": "JSONStore Save Test",
        }

        store.save(
            test_file,
            data_v3,
        )

        result_4 = store.load(
            test_file,
        )

        print("save() 后读取结果：")
        print(result_4)

        assert result_4 == data_v3

        print("PASS")

        # ==================================================
        # 7. 测试 reload()
        # ==================================================

        print_section("7. 测试 reload()")

        data_v4 = {
            "version": 4,
            "name": "JSONStore Reload Test",
        }

        with test_file.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data_v4,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

        result_5 = store.reload(
            test_file,
        )

        print("reload() 读取结果：")
        print(result_5)

        assert result_5 == data_v4

        print("PASS")

        # ==================================================
        # 8. 测试 invalidate()
        # ==================================================

        print_section("8. 测试 invalidate()")

        store.invalidate(
            test_file,
        )

        result_6 = store.load(
            test_file,
        )

        print("invalidate() 后读取结果：")
        print(result_6)

        assert result_6 == data_v4

        print("PASS")

        # ==================================================
        # 9. 测试 default
        # ==================================================

        print_section("9. 测试文件不存在时的 default")

        missing_file = (
            temp_dir / "missing.json"
        )

        default_data = {
            "pages": {}
        }

        result_7 = store.load(
            missing_file,
            default=default_data,
        )

        print("default 返回结果：")
        print(result_7)

        assert result_7 == default_data

        print("PASS")

        # ==================================================
        # 10. 最终结果
        # ==================================================

        print_section("测试完成")

        print("JSONStore 全部测试通过。")


if __name__ == "__main__":
    main()