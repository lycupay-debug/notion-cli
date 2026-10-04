from notion.databases import get_database


DATABASE_ID = "7df68966-1664-4a96-87cb-4a48b74dd824"


def main():
    result = get_database(DATABASE_ID)

    print("=" * 60)
    print("Database Retrieve Test")
    print("=" * 60)

    print("object:", result.get("object"))
    print("id:", result.get("id"))

    print("\n完整返回结果：")
    print(result)


if __name__ == "__main__":
    main()