from .client import notion


def get_page(page_id: str, *, filter_properties=None):
    """
    根据 Page ID 获取页面。

    filter_properties 为可选的属性 ID 列表。
    """
    kwargs = {}

    if filter_properties is not None:
        kwargs["filter_properties"] = filter_properties

    return notion.pages.retrieve(
        page_id=page_id,
        **kwargs,
    )


def get_page_property(
    page_id: str,
    property_id: str,
    *,
    start_cursor=None,
    page_size=None,
):
    """
    获取单个 Page Property 的完整结果。

    用于 relation / rollup 等可能存在分页结果的属性。
    """
    kwargs = {}

    if start_cursor is not None:
        kwargs["start_cursor"] = start_cursor
    if page_size is not None:
        kwargs["page_size"] = page_size

    return notion.pages.properties.retrieve(
        page_id=page_id,
        property_id=property_id,
        **kwargs,
    )


def update_page_properties(
    page_id: str,
    properties: dict,
    *,
    icon=None,
    cover=None,
    is_locked=None,
    template=None,
    erase_content=None,
    in_trash=None,
):
    """
    更新 Page。

    properties 保持原有业务调用方式；
    其余参数对应 2026-03-11 Page Update API。
    """
    kwargs = {
        "properties": properties,
    }

    if icon is not None:
        kwargs["icon"] = icon
    if cover is not None:
        kwargs["cover"] = cover
    if is_locked is not None:
        kwargs["is_locked"] = is_locked
    if template is not None:
        kwargs["template"] = template
    if erase_content is not None:
        kwargs["erase_content"] = erase_content
    if in_trash is not None:
        kwargs["in_trash"] = in_trash

    return notion.pages.update(
        page_id=page_id,
        **kwargs,
    )


def create_page(
    *,
    parent,
    properties=None,
    icon=None,
    cover=None,
    content=None,
    children=None,
    markdown=None,
    template=None,
    position=None,
    allow_async=None,
):
    """
    创建 Page。
    """
    kwargs = {
        "parent": parent,
    }

    if properties is not None:
        kwargs["properties"] = properties
    if icon is not None:
        kwargs["icon"] = icon
    if cover is not None:
        kwargs["cover"] = cover
    if content is not None:
        kwargs["content"] = content
    if children is not None:
        kwargs["children"] = children
    if markdown is not None:
        kwargs["markdown"] = markdown
    if template is not None:
        kwargs["template"] = template
    if position is not None:
        kwargs["position"] = position
    if allow_async is not None:
        kwargs["allow_async"] = allow_async

    return notion.pages.create(**kwargs)


def get_page_markdown(
    page_id: str,
    *,
    include_transcript=None,
):
    """
    使用 2026-03-11 Page Markdown API 获取页面内容。
    """
    kwargs = {}

    if include_transcript is not None:
        kwargs["include_transcript"] = include_transcript

    return notion.pages.retrieve_markdown(
        page_id=page_id,
        **kwargs,
    )


def update_page_markdown(
    page_id: str,
    *,
    allow_async=None,
    type=None,
    insert_content=None,
    replace_content_range=None,
    update_content=None,
    replace_content=None,
):
    """
    使用 2026-03-11 Page Markdown API 更新页面内容。
    """
    kwargs = {}

    if allow_async is not None:
        kwargs["allow_async"] = allow_async
    if type is not None:
        kwargs["type"] = type
    if insert_content is not None:
        kwargs["insert_content"] = insert_content
    if replace_content_range is not None:
        kwargs["replace_content_range"] = replace_content_range
    if update_content is not None:
        kwargs["update_content"] = update_content
    if replace_content is not None:
        kwargs["replace_content"] = replace_content

    return notion.pages.update_markdown(
        page_id=page_id,
        **kwargs,
    )


def move_page(page_id: str, *, parent):
    """
    移动 Page 到新的 parent。
    """
    return notion.pages.move(
        page_id=page_id,
        parent=parent,
    )


def get_page_identity(page_id: str):
    """
    获取页面的身份与归属信息。
    """
    page = get_page(page_id)

    return {
        "page_id": page["id"],
        "object": page.get("object"),
        "parent": page.get("parent"),
        "url": page.get("url"),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
        "in_trash": page.get("in_trash"),
        "is_locked": page.get("is_locked"),
    }
