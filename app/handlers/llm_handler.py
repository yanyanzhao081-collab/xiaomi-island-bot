"""LLM 意图处理器：根据意图执行录入、查询或兜底回复"""

import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import ReplyMessageRequestBody, ReplyMessageRequest

from app.config import Config
from app.services.llm import llm_service
from app.services.bitable import bitable_service
from app.services.chat_log import log_chat

# 复用飞书客户端
feishu_client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def _reply(message_id: str, text: str):
    """回复文本消息"""
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


async def process_text_message(message_id: str, text: str, sender_id: str = ""):
    """处理文本消息：LLM 意图识别 → 录入/查询/兜底"""

    result = await llm_service.analyze(text)
    intent = result.get("intent", "unknown")
    fields = result.get("fields", {})

    # ── 录入/更新 ──
    if intent == "record":
        app_name = fields.get("app_name", "")
        if not app_name:
            reply_text = "⚠️ 未能识别到应用名称，请再描述得具体一些，比如：拼多多预计26.4接入超级岛"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "录入失败-无应用名")
            return

        bitable_fields = llm_service.map_fields_to_bitable(fields)
        record_id = bitable_service.upsert_record(app_name, bitable_fields)

        if record_id:
            reply_text = f"✅ 已成功将 {app_name} 的进度录入超级岛大盘！"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "录入成功")
        else:
            reply_text = f"❌ 录入 {app_name} 时出现异常，请稍后重试。"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "录入异常")
        return

    # ── 删除 ──
    if intent == "delete":
        app_name = fields.get("app_name", "")
        scene = fields.get("scene", "")
        if not app_name:
            reply_text = "⚠️ 请告诉我要删除哪个应用的记录，比如：删除淘宝超市配送"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "删除失败-无应用名")
            return

        # 有场景则精确删除
        if scene:
            record = bitable_service.query_by_app_and_scene(app_name, scene)
        else:
            record = bitable_service.query_by_app_name(app_name)

        if record:
            ok = bitable_service.delete_record(record["record_id"])
            if ok:
                label = f"{app_name}（{scene}）" if scene else app_name
                reply_text = f"🗑️ 已删除 {label} 的记录。"
            else:
                reply_text = f"❌ 删除失败，请稍后重试。"
        else:
            label = f"{app_name}（{scene}）" if scene else app_name
            reply_text = f"🔍 未找到 {label} 的记录，无需删除。"
        _reply(message_id, reply_text)
        log_chat(sender_id, text, reply_text, "删除")
        return

    # ── 查询 ──
    if intent == "query":
        app_name = fields.get("app_name", "")
        scene = fields.get("scene", "")

        def _extract_val(f, name):
            """从 Bitable 字段中提取值，小窗/分享空值显示 ❌"""
            val = f.get(name, "")
            if isinstance(val, list) and len(val) > 0:
                val = val[0].get("text", "") if isinstance(val[0], dict) else str(val[0])
            if not val and name in ("支持小窗", "支持分享"):
                val = "❌"
            return val

        # 按场景查询（如"打车的有哪些"）
        if scene and not app_name:
            records = bitable_service.query_by_scene(scene)
            if records:
                lines = [f"📱 场景「{scene}」共 {len(records)} 条记录："]
                for r in records:
                    f = r["fields"]
                    name = f.get("应用名称", "")
                    if isinstance(name, list) and name:
                        name = name[0].get("text", "") if isinstance(name[0], dict) else str(name[0])
                    if name:
                        lines.append(f"  • {name}")
                reply_text = "\n".join(lines)
            else:
                reply_text = f"🔍 未找到场景「{scene}」的相关记录。"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "场景查询")
            return

        # 按应用名称查询
        if not app_name:
            reply_text = "⚠️ 请告诉我你要查询哪个应用或场景的进度，比如：查一下拼多多的进度，或者：打车的有哪些"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "查询失败-无关键词")
            return

        # 如果同时有应用名和场景，联合查询
        if scene:
            record = bitable_service.query_by_app_and_scene(app_name, scene)
            if record:
                f = record["fields"]
                lines = [f"📱 {app_name}（{scene}）的接入进度："]
                for name in ["场景", "大岛", "小岛", "接入版本", "进度排期", "支持小窗", "支持分享"]:
                    val = _extract_val(f, name)
                    if val:
                        lines.append(f"  • {name}：{val}")
                reply_text = "\n".join(lines)
            else:
                reply_text = f"🔍 未找到 {app_name} 的「{scene}」场景记录。"
            _reply(message_id, reply_text)
            log_chat(sender_id, text, reply_text, "查询")
            return

        record = bitable_service.query_by_app_name(app_name)
        if record:
            f = record["fields"]
            lines = [f"📱 {app_name} 的接入进度："]
            field_names = ["场景", "大岛", "小岛", "接入版本", "进度排期", "支持小窗", "支持分享"]
            for name in field_names:
                val = _extract_val(f, name)
                if val:
                    lines.append(f"  • {name}：{val}")
            reply_text = "\n".join(lines)
        else:
            reply_text = f"🔍 未找到 {app_name} 的相关记录。"
        _reply(message_id, reply_text)
        log_chat(sender_id, text, reply_text, "查询")
        return

    # ── 兜底 ──
    reply_text = "我是超级岛进度管家，您可以直接告诉我项目的进度（如：拼多多大岛正在测试），或者问我某个应用的进度哦。"
    _reply(message_id, reply_text)
    log_chat(sender_id, text, reply_text, "未识别")


async def process_text_message_readonly(message_id: str, text: str, sender_id: str = ""):
    """只读模式：只允许查询，录入请求返回无权限提示"""
    result = await llm_service.analyze(text)
    intent = result.get("intent", "unknown")
    fields = result.get("fields", {})

    if intent == "query":
        app_name = fields.get("app_name", "")
        if not app_name:
            _reply(message_id, "⚠️ 请告诉我你要查询哪个应用的进度，比如：查一下拼多多的进度")
            return
        record = bitable_service.query_by_app_name(app_name)
        if record:
            f = record["fields"]
            lines = [f"📱 {app_name} 的接入进度："]
            for name in ["场景", "大岛", "小岛", "接入版本", "进度排期", "支持小窗", "支持分享"]:
                val = f.get(name, "")
                if isinstance(val, list) and len(val) > 0:
                    val = val[0].get("text", "") if isinstance(val[0], dict) else str(val[0])
                if val:
                    lines.append(f"  • {name}：{val}")
            _reply(message_id, "\n".join(lines))
        else:
            _reply(message_id, f"🔍 未找到 {app_name} 的相关记录。")
    elif intent == "record":
        _reply(message_id, "⚠️ 抱歉，您没有录入权限。如需录入进度，请联系管理员开通。")
    else:
        _reply(message_id, "我是超级岛进度管家，您可以问我某个应用的进度，比如：查一下拼多多的进度。")
