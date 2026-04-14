"""精确指令处理器 — 录入模板、对接人、进度汇总"""

import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    ReplyMessageRequestBody, ReplyMessageRequest,
    CreateMessageRequestBody, CreateMessageRequest,
)
from app.config import Config
from app.services.bitable import bitable_service

feishu_client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def _reply_text(message_id: str, text: str):
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


def _reply_card(message_id: str, card_json: dict):
    body = ReplyMessageRequestBody.builder() \
        .content(json.dumps(card_json)) \
        .msg_type("interactive") \
        .build()
    req = ReplyMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(body) \
        .build()
    try:
        feishu_client.im.v1.message.reply(req)
    except Exception as e:
        print(f"回复卡片失败: {e}")


def send_contact_card(message_id: str):
    """发送对接人名单卡片"""
    card = {
        "header": {
            "title": {"tag": "plain_text", "content": "📋 超级岛对接人名单"},
            "template": "blue",
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "**岛运营**：赵琰琰\n📧 zhaoyanyan@xiaomi.com"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**mipush 运营**：汤德萍\n📧 v-tangdeping@xiaomi.com"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**岛产品**：张亚玲\n📧 zhangyaling1@xiaomi.com"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**岛后台产品**：赵巍\n📧 zhaowei45@xiaomi.com"}},
        ],
    }
    _reply_card(message_id, card)


def send_summary(message_id: str):
    """发送进度汇总卡片（含 Bitable 链接）"""
    records = bitable_service.query_all()
    total = len(records)

    # 统计场景分布
    scene_count = {}
    schedule_count = {}
    for r in records:
        fields = r.get("fields", {})
        # 提取场景
        scene = fields.get("场景", "")
        if isinstance(scene, list) and scene:
            scene = scene[0].get("text", "") if isinstance(scene[0], dict) else str(scene[0])
        if scene:
            scene_count[scene] = scene_count.get(scene, 0) + 1
        # 提取进度
        schedule = fields.get("进度排期", "")
        if isinstance(schedule, list) and schedule:
            schedule = schedule[0].get("text", "") if isinstance(schedule[0], dict) else str(schedule[0])
        if schedule:
            schedule_count[schedule] = schedule_count.get(schedule, 0) + 1

    # 构建卡片
    scene_lines = "\n".join([f"• {k}：{v} 个" for k, v in scene_count.items()]) or "暂无数据"
    schedule_lines = "\n".join([f"• {k}：{v} 个" for k, v in sorted(schedule_count.items(), key=lambda x: -x[1])[:5]]) or "暂无数据"

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**📊 总应用数**：{total} 条记录"}},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**场景分布**\n{scene_lines}"}},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**进度分布 (Top 5)**\n{schedule_lines}"}},
    ]

    bitable_url = Config.BITABLE_URL
    if bitable_url:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📊 点击查看完整进度表格"},
                "url": bitable_url,
                "type": "primary",
            }],
        })

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": "🏝️ 超级岛进度汇总"},
            "template": "green",
        },
        "elements": elements,
    }
    _reply_card(message_id, card)
