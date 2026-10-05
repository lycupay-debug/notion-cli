from .client import notion


def get_page(page_id: str):
    """根据 Page ID 获取页面信息。"""
    return notion.pages.retrieve(page_id=page_id)


def update_page_properties(page_id: str, properties: dict):
    """更新 Notion 页面属性。"""
    return notion.pages.update(
        page_id=page_id,
        properties=properties,
    )


def get_page_identity(page_id: str):
    """
    获取页面的身份与归属信息。

    返回：
    - page_id
    - object
    - parent
    - url
    - created_time
    - last_edited_time
    """
    page = get_page(page_id)

    return {
        "page_id": page["id"],
        "object": page.get("object"),
        "parent": page.get("parent"),
        "url": page.get("url"),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
    }