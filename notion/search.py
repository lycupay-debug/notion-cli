from .client import notion


def search(
    query: str = "",
    *,
    object_type: str = "page",
    sort=None,
    start_cursor=None,
    page_size=100,
):
    """
    使用 Notion Search API。

    2026-03-11 支持按 object 类型筛选：
    - page
    - data_source
    """
    if object_type not in {"page", "data_source"}:
        raise ValueError(
            f"不支持的 object_type: {object_type}"
        )

    response = notion.search(
        query=query,
        filter={
            "property": "object",
            "value": object_type,
        },
        sort=sort
        or {
            "direction": "descending",
            "timestamp": "last_edited_time",
        },
        start_cursor=start_cursor,
        page_size=page_size,
    )

    return response


def search_pages(query: str = "", **kwargs):
    """
    向后兼容：只搜索 Page。
    """
    response = search(
        query=query,
        object_type="page",
        **kwargs,
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
