from .client import notion


def get_data_source(data_source_id: str):
    """
    获取 Notion Data Source 的完整定义。

    返回 Notion API 返回的原始 Data Source 对象。
    其中 properties 保存该 Data Source 的全部字段属性定义。
    """
    return notion.data_sources.retrieve(
        data_source_id=data_source_id
    )