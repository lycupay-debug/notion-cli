from notion.pages import get_page_identity


PAGE_IDS = [
    "3eb7613b-20a9-816a-a6e9-e55fcbc05115",
    "3ec7613b-20a9-8181-afc5-f7327007d04b",
    "3eb7613b-20a9-81a9-a86c-f79d9797abf0",
    "3eb7613b-20a9-81e4-8765-c572c08b7115",
    "3eb7613b-20a9-81e3-ac95-d826a43ecc14",
]


def main():
    print("=" * 80)
    print("Page Identity 批量归属测试")
    print("=" * 80)

    for index, page_id in enumerate(PAGE_IDS, 1):
        print(f"\n[{index}] Page ID")
        print(page_id)

        try:
            identity = get_page_identity(page_id)

            print("object:")
            print(identity.get("object"))

            parent = identity.get("parent") or {}

            print("parent:")
            print(parent)

            print("data_source_id:")
            print(parent.get("data_source_id"))

        except Exception as e:
            print("ERROR:")
            print(f"{type(e).__name__}: {e}")

        print("-" * 80)


if __name__ == "__main__":
    main()