from .client import notion


def retrieve_database(database_id: str):
    return notion.databases.retrieve(
        database_id=database_id,
    )


def update_database(
    database_id: str,
    *,
    parent=None,
    title=None,
    description=None,
    is_inline=None,
    icon=None,
    cover=None,
    in_trash=None,
    is_locked=None,
):
    kwargs = {}

    if parent is not None:
        kwargs["parent"] = parent
    if title is not None:
        kwargs["title"] = title
    if description is not None:
        kwargs["description"] = description
    if is_inline is not None:
        kwargs["is_inline"] = is_inline
    if icon is not None:
        kwargs["icon"] = icon
    if cover is not None:
        kwargs["cover"] = cover
    if in_trash is not None:
        kwargs["in_trash"] = in_trash
    if is_locked is not None:
        kwargs["is_locked"] = is_locked

    return notion.databases.update(
        database_id=database_id,
        **kwargs,
    )


def create_database(
    *,
    parent,
    title,
    description=None,
    is_inline=None,
    initial_data_source=None,
    icon=None,
    cover=None,
):
    kwargs = {
        "parent": parent,
        "title": title,
    }

    if description is not None:
        kwargs["description"] = description
    if is_inline is not None:
        kwargs["is_inline"] = is_inline
    if initial_data_source is not None:
        kwargs["initial_data_source"] = initial_data_source
    if icon is not None:
        kwargs["icon"] = icon
    if cover is not None:
        kwargs["cover"] = cover

    return notion.databases.create(**kwargs)
