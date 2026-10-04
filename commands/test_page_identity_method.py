from notion.pages import get_page_identity


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"


def main():
    identity = get_page_identity(PAGE_ID)

    print("=" * 80)
    print("页面身份验证")
    print("=" * 80)

    print("Page ID：")
    print(identity["page_id"])

    print("\nObject：")
    print(identity["object"])

    print("\nParent：")
    print(identity["parent"])

    print("\nURL：")
    print(identity["url"])

    print("\n最后编辑：")
    print(identity["last_edited_time"])


if __name__ == "__main__":
    main()