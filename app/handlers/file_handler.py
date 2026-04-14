"""本地文件（Excel/CSV）解析处理器"""

import json
import pandas as pd
import lark_oapi as lark
from lark_oapi.api.im.v1 import ReplyMessageRequestBody, ReplyMessageRequest

from app.config import Config
from app.services.feishu_file import download_file, cleanup_file
from app.services.bitable import bitable_service
from app.utils.field_mapper import map_columns

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


def process_file_message(message_id: str, file_key: str, file_name: str, reply_to_id: str = ""):
    """处理用户上传的 Excel/CSV 文件。message_id 用于下载文件，reply_to_id 用于回复（引用场景）"""
    reply_id = reply_to_id or message_id
    local_path = ""
    try:
        # 1. 判断文件类型
        lower_name = file_name.lower()
        if not (lower_name.endswith(".xlsx") or lower_name.endswith(".csv") or lower_name.endswith(".xls")):
            _reply(reply_id, f"⚠️ 暂不支持该文件格式，请上传 .xlsx 或 .csv 文件。")
            return

        # 2. 下载文件
        _reply(reply_id, f"📥 正在下载并解析文件 [{file_name}]，请稍候...")
        local_path = download_file(message_id, file_key, file_name)
        if not local_path:
            _reply(reply_id, "❌ 文件下载失败，请重试。")
            return

        # 3. 解析文件（不预填空，保留 NaN 用于合并单元格检测）
        if lower_name.endswith(".csv"):
            df = pd.read_csv(local_path, dtype=str)
        else:
            df = pd.read_excel(local_path, dtype=str, engine="openpyxl")

        if df.empty:
            _reply(reply_id, "⚠️ 文件内容为空，请检查后重新上传。")
            return

        # 4. 列名映射
        df = map_columns(df)
        if "应用名称" not in df.columns:
            _reply(reply_id, "⚠️ 未找到「应用名称」列，请确保表格中包含应用名称字段。")
            return

        # 4.5 处理合并单元格：应用名称列向下填充
        df["应用名称"] = df["应用名称"].ffill()
        df = df.fillna("")

        # 5. 构建记录并校验
        records = []
        errors = []
        for idx, row in df.iterrows():
            app_name = str(row.get("应用名称", "")).strip()
            if not app_name:
                errors.append(f"第 {idx + 2} 行：应用名称为空，已跳过")
                continue
            record = {k: str(v).strip() for k, v in row.items() if str(v).strip()}
            records.append(record)

        if not records:
            _reply(reply_id, "⚠️ 没有有效数据可录入，请检查表格内容。")
            return

        # 6. 批量写入 Bitable
        result = bitable_service.batch_create_records(records)
        success = result["success"]
        failed = result["failed"]

        # 7. 回复结果
        lines = [f"📊 文件 [{file_name}] 解析完成："]
        lines.append(f"  ✅ 成功录入：{success} 条")
        if failed > 0:
            lines.append(f"  ❌ 失败：{failed} 条")
        if errors:
            lines.append(f"  ⚠️ 跳过：{len(errors)} 条")
            for e in errors[:5]:  # 最多显示5条错误
                lines.append(f"    - {e}")
            if len(errors) > 5:
                lines.append(f"    - ...还有 {len(errors) - 5} 条")

        _reply(reply_id, "\n".join(lines))

    except Exception as e:
        print(f"process_file_message 异常: {e}")
        _reply(reply_id, f"❌ 文件处理出错：{e}")

    finally:
        if local_path:
            cleanup_file(local_path)
