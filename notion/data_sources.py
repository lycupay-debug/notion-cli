from .client import notion


def get_data_source(data_source_id: str):
    """
    获取 Data Source 的完整定义。

    2026-03-11:
    Data Source 是数据库容器下真正承载 schema / properties 的对象。
    """
    return notion.data_sources.retrieve(
        data_source_id=data_source_id,
    )


def query_data_source(
    data_source_id: str,
    *,
    filter_properties=None,
    sorts=None,
    filter=None,
    start_cursor=None,
    page_size=None,
    in_trash=None,
    result_type=None,
):
    """
    查询 Data Source 中的页面 / Data Source。

    所有参数均对应 2026-03-11 Data Source Query API。
    """
    kwargs = {}

    if filter_properties is not None:
        kwargs["filter_properties"] = filter_properties
    if sorts is not None:
        kwargs["sorts"] = sorts
    if filter is not None:
        kwargs["filter"] = filter
    if start_cursor is not None:
        kwargs["start_cursor"] = start_cursor
    if page_size is not None:
        kwargs["page_size"] = page_size
    if in_trash is not None:
        kwargs["in_trash"] = in_trash
    if result_type is not None:
        kwargs["result_type"] = result_type

    return notion.data_sources.query(
        data_source_id=data_source_id,
        **kwargs,
    )


def update_data_source(
    data_source_id: str,
    *,
    title=None,
    icon=None,
    properties=None,
    in_trash=None,
    parent=None,
):
    """
    更新 Data Source。

    对应 2026-03-11 Update a Data Source API。
    """
    kwargs = {}

    if title is not None:
        kwargs["title"] = title
    if icon is not None:
        kwargs["icon"] = icon
    if properties is not None:
        kwargs["properties"] = properties
    if in_trash is not None:
        kwargs["in_trash"] = in_trash
    if parent is not None:
        kwargs["parent"] = parent

    return notion.data_sources.update(
        data_source_id=data_source_id,
        **kwargs,
    )


def create_data_source(
    *,
    parent,
    properties=None,
    title=None,
    icon=None,
):
    """
    在现有 Database 下创建 Data Source。
    """
    kwargs = {
        "parent": parent,
    }

    if properties is not None:
        kwargs["properties"] = properties
    if title is not None:
        kwargs["title"] = title
    if icon is not None:
        kwargs["icon"] = icon

    return notion.data_sources.create(**kwargs)


def list_data_source_templates(
    data_source_id: str,
    *,
    name=None,
    start_cursor=None,
    page_size=None,
):
    """
    获取 Data Source 可用的页面模板。
    """
    kwargs = {}

    if name is not None:
        kwargs["name"] = name
    if start_cursor is not None:
        kwargs["start_cursor"] = start_cursor
    if page_size is not None:
        kwargs["page_size"] = page_size

    return notion.data_sources.list_templates(
        data_source_id=data_source_id,
        **kwargs,
    )
