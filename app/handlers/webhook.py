"""飞书 Webhook 事件处理"""

import re
import json
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from app.config import Config
from app.handlers.llm_handler import process_text_message
from app.handlers.file_handler import process_file_message
from app.handlers.link_handler import process_link_message
from app.handlers.command_handler import send_contact_card, send_summary
from app.utils.link_parser import contains_feishu_link

router = APIRouter()

# ── 录入权限白名单（open_id），从 .env 读取 ──
ADMIN_IDS = set(filter(None, Config.ADMIN_OPEN_IDS.split(","))) if hasattr(Config, "ADMIN_OPEN_IDS") and Config.ADMIN_OPEN_IDS else set()
NO_PERMISSION_MSG = "⚠️ 抱歉，您没有录入权限。如需录入进度，请联系管理员开通。\n当前支持的查询功能：发送「进度汇总」「对接人」或「查一下XX的进度」。"


def _get_sender_open_id(event: dict) -> str:
    """从事件中提取发送者 open_id"""
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    return sender_id.get("open_id", "")


def _has_write_permission(open_id: str) -> bool:
    """检查用户是否有录入权限。如果白名单为空则所有人都有权限"""
    if not ADMIN_IDS:
        return True
    return open_id in ADMIN_IDS


def _reply_text_msg(message_id: str, text: str):
    """快速回复文本（用于精确指令）"""
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import ReplyMessageRequestBody, ReplyMessageRequest
    client = lark.Client.builder() \
        .app_id(Config.FEISHU_APP_ID) \
        .app_secret(Config.FEISHU_APP_SECRET) \
        .build()
    body = ReplyMessageRequestBody.builder() \
        .content(json.dumps({"text": text})) \
        .msg_type("text") \
        .build()
    req = ReplyMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(body) \
        .build()
    try:
        client.im.v1.message.reply(req)
    except Exception as e:
        print(f"回复失败: {e}")


def _clean_mention(text: str) -> str:
    """清理飞书消息中的 @mention 标记"""
    return re.sub(r"@_\w+\s*", "", text).strip()


def _run_async_task(message_id: str, text: str, sender_id: str = ""):
    """在新的事件循环中运行异步任务"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_text_message(message_id, text, sender_id))
    except Exception as e:
        print(f"后台任务异常: {e}")
    finally:
        loop.close()


def _run_async_readonly(message_id: str, text: str, sender_id: str = ""):
    """无权限用户的只读模式"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from app.handlers.llm_handler import process_text_message_readonly
        loop.run_until_complete(process_text_message_readonly(message_id, text, sender_id))
    except Exception as e:
        print(f"只读任务异常: {e}")
    finally:
        loop.close()


@router.post("/event")
async def handle_event(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    print(f"[Webhook] 收到事件: {json.dumps(data, ensure_ascii=False)[:500]}")

    # 1. 飞书 URL Challenge 验证
    if data.get("type") == "url_verification":
        if data.get("token") != Config.FEISHU_VERIFY_TOKEN:
            return JSONResponse(content={"error": "Invalid Token"}, status_code=400)
        return JSONResponse(content={"challenge": data.get("challenge")})

    # 2. 处理消息事件
    header = data.get("header", {})
    if header.get("event_type") == "im.message.receive_v1":
        event = data.get("event", {})
        message = event.get("message", {})
        message_id = message.get("message_id")
        msg_type = message.get("message_type", "")
        sender_open_id = _get_sender_open_id(event)

        print(f"[Webhook] message_id={message_id}, msg_type={msg_type}, sender={sender_open_id}")

        # ── 优先级 1：文件消息 → 表格解析（需要权限）──
        if msg_type == "file" and message_id:
            if not _has_write_permission(sender_open_id):
                _reply_text_msg(message_id, NO_PERMISSION_MSG)
                return JSONResponse(content={"msg": "ok"})
            content_str = message.get("content", "{}")
            try:
                content = json.loads(content_str)
            except json.JSONDecodeError:
                content = {}
            file_key = content.get("file_key", "")
            file_name = content.get("file_name", "")
            print(f"[Webhook] 文件消息: file_key={file_key}, file_name={file_name}")
            if file_key and file_name:
                background_tasks.add_task(process_file_message, message_id, file_key, file_name)
            return JSONResponse(content={"msg": "ok"})

        # ── 优先级 6：文本消息 → LLM 意图识别 ──
        if msg_type == "text" and message_id:
            content_str = message.get("content", "{}")
            try:
                raw_text = json.loads(content_str).get("text", "")
            except (json.JSONDecodeError, AttributeError):
                raw_text = ""

            text = _clean_mention(raw_text)
            print(f"[Webhook] 清理后文本: {text}")

            if text:
                # ── 优先级 2：录入模板（需要权限）──
                if text in ("录入模板", "模板"):
                    if _has_write_permission(sender_open_id):
                        _reply_text_msg(message_id, "📝 录入模板功能开发中，请直接用自然语言告诉我进度信息即可。\n例如：拼多多预计26.4接入超级岛，有大岛，支持小窗")
                    else:
                        _reply_text_msg(message_id, NO_PERMISSION_MSG)
                # ── 优先级 3：对接人（所有人可用）──
                elif text == "对接人":
                    background_tasks.add_task(send_contact_card, message_id)
                # ── 优先级 4：进度汇总（所有人可用）──
                elif text in ("进度汇总", "汇总"):
                    background_tasks.add_task(send_summary, message_id)
                # ── 优先级 5：飞书表格链接（需要权限）──
                elif contains_feishu_link(text):
                    if _has_write_permission(sender_open_id):
                        background_tasks.add_task(process_link_message, message_id, text)
                    else:
                        _reply_text_msg(message_id, NO_PERMISSION_MSG)
                # ── 优先级 6：LLM 意图识别（LLM 内部区分录入/查询）──
                else:
                    if _has_write_permission(sender_open_id):
                        background_tasks.add_task(_run_async_task, message_id, text, sender_open_id)
                    else:
                        background_tasks.add_task(_run_async_readonly, message_id, text, sender_open_id)

    return JSONResponse(content={"msg": "ok"})
