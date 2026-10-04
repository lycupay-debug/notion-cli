from notion.databases import query_system_ledger


results = query_system_ledger()

print(f"系统结构总账返回 {len(results)} 条记录")

for item in results[:10]:
    print(item["id"])