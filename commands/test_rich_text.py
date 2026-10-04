from notion.client import notion


PAGE_ID = "3eb7613b20a98138809bee3da6edfe84"

page = notion.pages.retrieve(page_id=PAGE_ID)

prop = page["properties"]["数据源链接和快捷链接"]

print("=" * 80)
print("属性类型：")
print(prop["type"])

print("\n完整属性结构：")
print(prop)