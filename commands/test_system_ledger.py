from commands.system_ledger import query_system_ledger


results = query_system_ledger()

print(f"系统结构总账返回 {len(results)} 条记录")

for index, item in enumerate(results[:5], start=1):
    print(f"{index}. {item['id']}")