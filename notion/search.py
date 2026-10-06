from .client import notion


def search(
    query: str = "",
    *,
    object_type=None,
    sort=None,
    start_cursor=None,
    page_size=None,
):
    kwargs = {
        "query": query,
    }

    if object_type is not None:
        kwargs["filter"] = {
            "property": "object",
            "value": object_type,
        }
    if sort is not None:
        kwargs["sort"] = sort
    if start_cursor is not None:
        kwargs["start_cursor"] = start_cursor
    if page_size is not None:
        kwargs["page_size"] = page_size

    return notion.search(**kwargs)
