from notion.pages import create_page


DATA_SOURCE_ID = "9c7afd69-cba9-44c3-ae20-ad2886498e96"


def main():
    try:
        result = create_page(
            parent={
                "data_source_id": DATA_SOURCE_ID,
            },
            properties={
                "名称": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "CLI临时写入测试",
                            },
                        }
                    ]
                }
            },
        )

        page_id = result.get("id")

        print("成功")
        print(f"page_id: {page_id}")

    except Exception as e:
        print("失败")
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()