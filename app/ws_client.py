"""飞书长连接 (WebSocket) 事件客户端 — 替代 Webhook 模式"""

import re
import json
import threading
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1, ReplyMessageRequestBody, ReplyMessageRequest, GetMessageRequest

from app.config import Config
from app.handlers.llm_handler import process_text_message, process_text_message_readonly
from app.handlers.file_handler import process_file_message
from app.handlers.link_handler import process_link_message
from app.handlers.command_handler import send_contact_card, send_summary
from app.utils.link_parser import contains_feishu_link

# ── 权限白名单 ──
ADMIN_IDS = set(filter(None, Config.ADMIN_OPEN_IDS.split(","))) if Config.ADMIN_OPEN_IDS else set()
NO_PERMISSION_MSG = "⚠️ 抱歉，您没有录入权限。如需录入进度，请联系管理员开通。\n当前支持的查询功能：发送「进度汇总」「对接人」或「查一下XX的进度」。"

# ── 飞书客户端 ──
feishu_client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def _clean_mention(text: str) -> str:
    return re.sub(r"@_\w+\s*", "", text).strip()


def _has_write_permission(open_id: str) -> bool:
    if not ADMIN_IDS:
        return True
    return open_id in ADMIN_IDS


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
        print(f"回复失败: {e}")


def _run_async(coro):
    """在新线程中运行异步协程"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    except Exception as e:
        print(f"异步任务异常: {e}")
    finally:
        loop.close()


def _get_parent_message(parent_id: str) -> dict:
    """获取被引用的原始消息，返回 {msg_type, content}"""
    try:
        req = GetMessageRequest.builder().message_id(parent_id).build()
        resp = feishu_client.im.v1.message.get(req)
        if resp.success() and resp.data.items:
            msg = resp.data.items[0]
            return {
                "msg_type": msg.msg_type,
                "content": msg.body.content if msg.body else "",
            }
    except Exception as e:
        print(f"获取引用消息失败: {e}")
    return {}


def _handle_message(data: P2ImMessageReceiveV1) -> None:
    """处理接收到的消息事件"""
    event = data.event
    message = event.message
    sender = event.sender

    message_id = message.message_id
    msg_type = message.message_type
    chat_type = message.chat_type if hasattr(message, 'chat_type') else ""
    sender_open_id = sender.sender_id.open_id if sender and sender.sender_id else ""

    print(f"[WS] message_id={message_id}, msg_type={msg_type}, chat_type={chat_type}, sender={sender_open_id}")
    print(f"[WS] content={message.content}")

    # ── 优先级 1：文件消息 ──
    if msg_type == "file" and message_id:
        if not _has_write_permission(sender_open_id):
            _reply_text(message_id, NO_PERMISSION_MSG)
            return
        try:
            content = json.loads(message.content)
        except (json.JSONDecodeError, TypeError):
            content = {}
        file_key = content.get("file_key", "")
        file_name = content.get("file_name", "")
        if file_key and file_name:
            threading.Thread(target=process_file_message, args=(message_id, file_key, file_name)).start()
        return

    # ── 文本消息 ──
    if msg_type == "text" and message_id:
        try:
            raw_text = json.loads(message.content).get("text", "")
        except (json.JSONDecodeError, TypeError, AttributeError):
            raw_text = ""

        text = _clean_mention(raw_text)
        print(f"[WS] 文本: {text}")

        # ── 引用回复检测：如果引用了一个文件消息，自动处理该文件 ──
        parent_id = message.parent_id if hasattr(message, 'parent_id') and message.parent_id else ""
        if parent_id and text:
            keywords = ["记录", "录入", "导入", "同步", "解析", "记录进度"]
            if any(kw in text for kw in keywords):
                if not _has_write_permission(sender_open_id):
                    _reply_text(message_id, NO_PERMISSION_MSG)
                    return
                parent_msg = _get_parent_message(parent_id)
                if parent_msg.get("msg_type") == "file":
                    try:
                        parent_content = json.loads(parent_msg.get("content", "{}"))
                        file_key = parent_content.get("file_key", "")
                        file_name = parent_content.get("file_name", "")
                        if file_key and file_name:
                            print(f"[WS] 引用文件: {file_name}, 用 parent_id={parent_id} 下载")
                            threading.Thread(target=process_file_message, args=(parent_id, file_key, file_name, message_id)).start()
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass
                _reply_text(message_id, "⚠️ 被引用的消息不是文件，请直接发送 Excel/CSV 文件给我。")
                return

        if not text:
            return

        # 优先级 2：录入模板
        if text in ("录入模板", "模板"):
            if _has_write_permission(sender_open_id):
                _reply_text(message_id, "📝 请直接用自然语言告诉我进度信息即可。\n例如：拼多多预计26.4接入超级岛，有大岛，支持小窗")
            else:
                _reply_text(message_id, NO_PERMISSION_MSG)
            return

        # 优先级 3：对接人
        if text == "对接人":
            send_contact_card(message_id)
            return

        # 优先级 4：进度汇总
        if text in ("进度汇总", "汇总"):
            send_summary(message_id)
            return

        # 优先级 4.5：清空表格（仅管理员）
        if text in ("清空表格", "清空数据"):
            if _has_write_permission(sender_open_id):
                _reply_text(message_id, "🗑️ 正在清空表格数据，请稍候...")
                from app.services.bitable import bitable_service
                deleted = bitable_service.delete_all_records()
                _reply_text(message_id, f"✅ 已清空 {deleted} 条记录，表格已重置。")
            else:
                _reply_text(message_id, NO_PERMISSION_MSG)
            return

        # 优先级 5：飞书链接
        if contains_feishu_link(text):
            if _has_write_permission(sender_open_id):
                threading.Thread(target=process_link_message, args=(message_id, text)).start()
            else:
                _reply_text(message_id, NO_PERMISSION_MSG)
            return

        # 优先级 6：LLM 意图识别
        if _has_write_permission(sender_open_id):
            threading.Thread(target=_run_async, args=(process_text_message(message_id, text, sender_open_id),)).start()
        else:
            threading.Thread(target=_run_async, args=(process_text_message_readonly(message_id, text, sender_open_id),)).start()


def start_ws_client():
    """启动飞书长连接客户端"""
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(_handle_message) \
        .build()

    cli = lark.ws.Client(
        Config.FEISHU_APP_ID,
        Config.FEISHU_APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )

    print("🚀 飞书长连接客户端启动中...")
    cli.start()
