from notion.pages import get_page


PAGE_ID = "3eb7613b-20a9-816a-a6e9-e55fcbc05115"
PROPERTY = "数据源链接和快捷链接"


page = get_page(PAGE_ID)

prop = page["properties"].get(PROPERTY)

print("=" * 80)
print("属性名称：", PROPERTY)
print("=" * 80)

if prop is None:
    print("属性不存在")
else:
    print("属性类型：")
    print(prop.get("type"))

    print("\n完整属性对象：")
    print(prop)

print("=" * 80)