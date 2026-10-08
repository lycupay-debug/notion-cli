import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notion.pages import create_page


DATA_SOURCE_ID = "3f37613b-20a9-80be-9269-000b34c8c046"


def main():
    success = 0
    failed = 0

    for i in range(1, 51):
        properties = {
            "名称": {
                "title": [
                    {
                        "text": {
                            "content": f"CLI测试-{i:03d}"
                        }
                    }
                ]
            },
            "序号": {
                "rich_text": [
                    {
                        "text": {
                            "content": f"{i:03d}"
                        }
                    }
                ]
            },
        }

        try:
            result = create_page(
                parent={"data_source_id": DATA_SOURCE_ID},
                properties=properties,
            )
            page_id = result.get("id", "unknown")
            print(f"[SUCCESS] {i:03d}/050 page_id={page_id}")
            success += 1
        except Exception as exc:
            print(f"[FAILED] {i:03d}/050 {type(exc).__name__}: {exc}")
            failed += 1

    print("=" * 60)
    print(f"完成: 成功={success}, 失败={failed}, 总数=50")


if __name__ == "__main__":
    main()
