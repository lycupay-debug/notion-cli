import os

from dotenv import load_dotenv
from notion_client import Client


load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

if not NOTION_TOKEN:
    raise RuntimeError("未找到 NOTION_TOKEN，请检查 .env 文件")


notion = Client(
    auth=NOTION_TOKEN,
    notion_version="2026-03-11",
)