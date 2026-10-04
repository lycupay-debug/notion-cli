from notion.object_resolver import resolve_notion_id


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"

DATABASE_ID = "7df68966-1664-4a96-87cb-4a48b74dd824"

INVALID_ID = "00000000-0000-0000-0000-000000000000"


def print_result(name, result):
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")


def main():
    page_result = resolve_notion_id(PAGE_ID)
    print_result("PAGE TEST", page_result)

    database_result = resolve_notion_id(DATABASE_ID)
    print_result("DATABASE TEST", database_result)

    invalid_result = resolve_notion_id(INVALID_ID)
    print_result("INVALID TEST", invalid_result)


if __name__ == "__main__":
    main()