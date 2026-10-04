from notion.databases import query_data_source


SYSTEM_LEDGER_ID = "9c7afd69-cba9-44c3-ae20-ad2886498e96"


def query_system_ledger():
    """查询系统结构总账"""
    return query_data_source(SYSTEM_LEDGER_ID)