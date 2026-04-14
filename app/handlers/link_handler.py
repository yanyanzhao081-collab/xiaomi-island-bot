"""飞书表格链接解析处理器"""

import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import ReplyMessageRequestBody, ReplyMessageRequest

from app.config import Config
from app.utils.link_parser import extract_feishu_links
from app.utils.field_mapper import map_columns
from app.services.feishu_sheet import read_bitable, read_sheet
from app.services.bitable import bitable_service
import pandas as pd

feishu_client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def _reply(message_id: str, text: str):
    body = ReplyMessageRequestBody.builder() \
        .content(json.dumps({"text": text})) \
        .msg_type("text") \
        .build()
    req = ReplyMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(body) \
        .build()
    try:
        feishu_client.im.v1.message.reply(req)
    except Exception as e:
        print(f"回复消息失败: {e}")


def process_link_message(message_id: str, text: str):
    """处理包含飞书表格链接的消息"""
    links = extract_feishu_links(text)
    if not links:
        return

    _reply(message_id, f"🔗 检测到 {len(links)} 个飞书表格链接，正在同步数据...")

    total_success = 0
    total_failed = 0

    for link in links:
        if link["type"] == "bitable":
            rows = read_bitable(link["token"], link["table_id"])
        elif link["type"] == "sheet":
            rows = read_sheet(link["token"], link.get("table_id", ""))
        else:
            continue

        if not rows:
            _reply(message_id, f"⚠️ 未能从链接中读取到数据，请检查链接权限。")
            continue

        # 转为 DataFrame 做列名映射
        df = pd.DataFrame(rows).fillna("")
        df = map_columns(df)

        if "应用名称" not in df.columns:
            _reply(message_id, "⚠️ 源表格中未找到「应用名称」列。")
            continue

        # 构建记录
        records = []
        for _, row in df.iterrows():
            app_name = str(row.get("应用名称", "")).strip()
            if app_name:
                record = {k: str(v).strip() for k, v in row.items() if str(v).strip()}
                records.append(record)

        if records:
            result = bitable_service.batch_create_records(records)
            total_success += result["success"]
            total_failed += result["failed"]

    lines = ["📊 飞书表格同步完成："]
    lines.append(f"  ✅ 成功录入：{total_success} 条")
    if total_failed > 0:
        lines.append(f"  ❌ 失败：{total_failed} 条")
    _reply(message_id, "\n".join(lines))
