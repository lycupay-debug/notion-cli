import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("NOTION_TOKEN")

if token:
    print("NOTION_TOKEN 读取成功")
    print(f"Token长度: {len(token)}")
else:
    print("未读取到 NOTION_TOKEN")