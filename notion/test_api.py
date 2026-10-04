import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

token = os.getenv("NOTION_TOKEN")

if not token:
    raise RuntimeError("未找到 NOTION_TOKEN")

notion = Client(auth=token)

response = notion.search(
    filter={
        "property": "object",
        "value": "page"
    }
)

print("Notion API 连接成功")
print(f"返回结果数量：{len(response['results'])}")

for page in response["results"][:5]:
    print(page["id"])