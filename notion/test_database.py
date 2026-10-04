from notion.client import notion


response = notion.search(
    filter={
        "property": "object",
        "value": "data_source",
    }
)

print(f"找到 {len(response['results'])} 个数据源")

for item in response["results"][:10]:
    print(item["id"])