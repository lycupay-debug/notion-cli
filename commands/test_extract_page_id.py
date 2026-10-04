import re

from notion.client import notion


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"
FIELD_NAME = "数据源链接和快捷链接"


def extract_page_id_from_url(url: str):
    """从 Notion 页面 URL 中提取并标准化 Page ID"""
    match = re.search(r"/p/([0-9a-fA-F]{32})", url)

    if not match:
        return None

    raw_id = match.group(1).lower()

    return (
        f"{raw_id[0:8]}-"
        f"{raw_id[8:12]}-"
        f"{raw_id[12:16]}-"
        f"{raw_id[16:20]}-"
        f"{raw_id[20:32]}"
    )


# 1. 读取系统结构总账记录
page = notion.pages.retrieve(page_id=PAGE_ID)

print("=" * 80)
print("当前记录：")
print(page["id"])

# 2. 获取目标字段
prop = page["properties"][FIELD_NAME]

print("\n字段类型：")
print(prop["type"])

# 3. 提取 URL
url = None

for item in prop.get("rich_text", []):
    if item.get("href"):
        url = item["href"]
        break

    text_data = item.get("text", {})
    link = text_data.get("link")

    if link and link.get("url"):
        url = link["url"]
        break

    plain_text = item.get("plain_text")
    if plain_text and plain_text.startswith("http"):
        url = plain_text
        break

print("\n提取出的 URL：")
print(url)

if not url:
    raise RuntimeError("没有找到 Notion URL")

# 4. 从 URL 提取 Page ID
target_page_id = extract_page_id_from_url(url)

print("\n解析出的 Page ID：")
print(target_page_id)

if not target_page_id:
    raise RuntimeError("无法从 URL 中解析 Page ID")

# 5. 调用 Notion API 验证目标页面
target_page = notion.pages.retrieve(page_id=target_page_id)

print("\nAPI 验证结果：")
print("对象类型：", target_page["object"])
print("页面 ID：", target_page["id"])
print("页面 URL：", target_page.get("url"))

print("\n验证成功。")
print("=" * 80)