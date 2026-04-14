"""飞书链接正则解析 — 从文本中提取 Bitable / Sheets 链接"""

import re

BITABLE_PATTERN = re.compile(
    r'https?://[\w.-]+\.feishu\.cn/base/(\w+)(?:\?table=(\w+))?'
)
SHEET_PATTERN = re.compile(
    r'https?://[\w.-]+\.feishu\.cn/sheets/(\w+)(?:\?sheet=(\w+))?'
)


def extract_feishu_links(text: str) -> list[dict]:
    """从文本中提取飞书表格链接，返回 [{type, token, table_id}]"""
    results = []

    for m in BITABLE_PATTERN.finditer(text):
        results.append({
            "type": "bitable",
            "token": m.group(1),
            "table_id": m.group(2) or "",
        })

    for m in SHEET_PATTERN.finditer(text):
        results.append({
            "type": "sheet",
            "token": m.group(1),
            "table_id": m.group(2) or "",  # sheet_id
        })

    return results


def contains_feishu_link(text: str) -> bool:
    return bool(BITABLE_PATTERN.search(text) or SHEET_PATTERN.search(text))
