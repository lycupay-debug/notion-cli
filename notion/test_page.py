from notion.pages import get_page


page_id = "3e17613b-20a9-8126-9ee9-f74545e50270"

page = get_page(page_id)

print("页面读取成功")
print(f"Page ID: {page['id']}")
print(f"对象类型: {page['object']}")