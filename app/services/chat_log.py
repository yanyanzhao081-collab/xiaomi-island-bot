"""聊天日志服务 — 记录所有交互历史到 Bitable"""

from datetime import datetime
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import (
    CreateAppTableRecordRequest, AppTableRecord,
)
from app.config import Config

client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def log_chat(user_id: str, user_msg: str, bot_reply: str, op_type: str):
    """记录一条聊天日志到 Bitable 操作日志表"""
    if not Config.BITABLE_LOG_TABLE_ID:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields = {
        "时间": now,
        "用户ID": user_id,
        "用户消息": user_msg[:500],
        "机器人回复": bot_reply[:500],
        "操作类型": op_type,
    }

    try:
        req = CreateAppTableRecordRequest.builder() \
            .app_token(Config.BITABLE_APP_TOKEN) \
            .table_id(Config.BITABLE_LOG_TABLE_ID) \
            .request_body(
                AppTableRecord.builder()
                .fields(fields)
                .build()
            ) \
            .build()
        resp = client.bitable.v1.app_table_record.create(req)
        if not resp.success():
            print(f"写入日志失败: {resp.msg}")
    except Exception as e:
        print(f"log_chat 异常: {e}")
