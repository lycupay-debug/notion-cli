from notion.search import search_pages


results = search_pages("辰氏数字大脑")

print(f"找到 {len(results)} 个结果")

for page in results[:10]:
    print(page["id"])