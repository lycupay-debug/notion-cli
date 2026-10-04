from notion.client import notion


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"


page = notion.pages.retrieve(page_id=PAGE_ID)

print("=" * 80)
print("页面 ID")
print(page["id"])

print("\n对象类型")
print(page["object"])

print("\n父级对象")
print(page.get("parent"))

print("\nURL")
print(page.get("url"))

print("\n创建时间")
print(page.get("created_time"))

print("\n最后编辑")
print(page.get("last_edited_time"))

print("\n属性")
for name, prop in page.get("properties", {}).items():
    print(f"- {name}: {prop.get('type')}")