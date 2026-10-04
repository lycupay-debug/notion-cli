from notion.client import notion


response = notion.search(
    sort={
        "direction": "descending",
        "timestamp": "last_edited_time",
    },
    page_size=20,
)

results = response["results"]

print(f"返回 {len(results)} 条记录")
print("=" * 80)

for index, item in enumerate(results, start=1):
    properties = item.get("properties", {})

    title = "（无标题）"

    for prop in properties.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            title = "".join(
                part.get("plain_text", "")
                for part in title_parts
            ) or "（无标题）"
            break

    print(f"{index}. {title}")
    print(f"   ID: {item['id']}")
    print(f"   最后编辑: {item.get('last_edited_time')}")
    print(f"   URL: {item.get('url')}")
    print()