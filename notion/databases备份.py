from .client import notion


def query_database(database_id: str, filter: dict | None = None, sorts: list | None = None):
    """查询 Notion 数据库"""
    kwargs = {}

    if filter:
        kwargs["filter"] = filter

    if sorts:
        kwargs["sorts"] = sorts

    response = notion.databases.query(
        database_id=database_id,
        **kwargs,
    )

    return response["results"]