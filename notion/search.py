from .client import notion


def search_pages(query: str = ""):
    """搜索 Notion 页面"""
    response = notion.search(
        query=query,
        filter={
            "property": "object",
            "value": "page",
        },
        sort={
            "direction": "descending",
            "timestamp": "last_edited_time",
        },
        page_size=100,
    )

    return response["results"]


def get_global_page_snapshot():
    """
    获取 GlobalWatcher 所需的最小页面状态。

    这里只保留：
    - Page ID
    - last_edited_time
    - URL
    """
    pages = search_pages()

    snapshot = []

    for page in pages:
        snapshot.append(
            {
                "id": page["id"],
                "last_edited_time": page["last_edited_time"],
                "url": page["url"],
            }
        )

    return snapshot