from notion.pages import get_page, update_page_properties


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"


def extract_notion_url(prop):
    """从 rich_text 中提取 URL"""

    for item in prop.get("rich_text", []):
        if item.get("href"):
            return item["href"]

        text = item.get("text", {})
        link = text.get("link")

        if link and link.get("url"):
            return link["url"]

        if item.get("plain_text", "").startswith("https://app.notion.com/"):
            return item["plain_text"]

    return None


def extract_page_id(url):
    """从 Notion 页面 URL 提取 32 位 Page ID，并转换成 UUID 格式"""

    if not url:
        raise RuntimeError("没有找到 Notion URL")

    marker = "/p/"
    if marker not in url:
        raise RuntimeError(f"不是 Notion 页面 URL：{url}")

    raw_id = url.split(marker, 1)[1].split("?", 1)[0].replace("-", "")

    if len(raw_id) != 32:
        raise RuntimeError(f"Page ID 长度异常：{raw_id}")

    return (
        f"{raw_id[:8]}-"
        f"{raw_id[8:12]}-"
        f"{raw_id[12:16]}-"
        f"{raw_id[16:20]}-"
        f"{raw_id[20:]}"
    )


print("=" * 80)
print("第一步：读取当前记录")

page = get_page(PAGE_ID)

source_prop = page["properties"]["数据源链接和快捷链接"]

url = extract_notion_url(source_prop)

print("源 URL：")
print(url)

print("\n第二步：解析 Page ID")

target_page_id = extract_page_id(url)

print("目标 Page ID：")
print(target_page_id)


print("\n第三步：API 验证目标页面")

target_page = get_page(target_page_id)

print("对象类型：", target_page["object"])
print("页面 ID：", target_page["id"])
print("页面 URL：", target_page.get("url"))

if target_page["id"] != target_page_id:
    raise RuntimeError("Page ID 验证失败")

print("目标页面验证成功。")


print("\n第四步：检查当前 Notion页面ID")

current_prop = page["properties"]["Notion页面ID"]

current_value = "".join(
    item.get("plain_text", "")
    for item in current_prop.get("rich_text", [])
)

print("当前值：")
print(current_value if current_value else "(空)")


if current_value == target_page_id:
    print("\n当前值已经正确，无需写入。")
else:
    print("\n第五步：写入 Notion页面ID")

    update_page_properties(
        PAGE_ID,
        {
            "Notion页面ID": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": target_page_id
                        }
                    }
                ]
            }
        }
    )

    print("写入完成。")


print("\n第六步：重新读取并验证")

updated_page = get_page(PAGE_ID)

updated_prop = updated_page["properties"]["Notion页面ID"]

updated_value = "".join(
    item.get("plain_text", "")
    for item in updated_prop.get("rich_text", [])
)

print("回读值：")
print(updated_value)

print("\n期望值：")
print(target_page_id)


if updated_value != target_page_id:
    raise RuntimeError(
        f"回读验证失败：实际值={updated_value!r}，期望值={target_page_id!r}"
    )

print("\n" + "=" * 80)
print("写入 + 回读验证成功")
print("=" * 80)