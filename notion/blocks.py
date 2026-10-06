from .client import notion


def retrieve_block(block_id: str):
    return notion.blocks.retrieve(
        block_id=block_id,
    )


def retrieve_block_children(
    block_id: str,
    *,
    start_cursor=None,
    page_size=None,
):
    kwargs = {}

    if start_cursor is not None:
        kwargs["start_cursor"] = start_cursor
    if page_size is not None:
        kwargs["page_size"] = page_size

    return notion.blocks.children.list(
        block_id=block_id,
        **kwargs,
    )


def append_block_children(
    block_id: str,
    children,
    *,
    position=None,
):
    kwargs = {
        "block_id": block_id,
        "children": children,
    }

    if position is not None:
        kwargs["position"] = position

    return notion.blocks.children.append(**kwargs)


def update_block(block_id: str, **kwargs):
    return notion.blocks.update(
        block_id=block_id,
        **kwargs,
    )


def delete_block(block_id: str):
    return notion.blocks.delete(
        block_id=block_id,
    )
