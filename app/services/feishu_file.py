"""飞书文件下载服务"""

import os
import lark_oapi as lark
from lark_oapi.api.im.v1 import GetMessageResourceRequest
from app.config import Config

TMP_DIR = "/tmp/island_bot"

client = lark.Client.builder() \
    .app_id(Config.FEISHU_APP_ID) \
    .app_secret(Config.FEISHU_APP_SECRET) \
    .build()


def download_file(message_id: str, file_key: str, file_name: str) -> str:
    os.makedirs(TMP_DIR, exist_ok=True)
    local_path = os.path.join(TMP_DIR, file_name)
    try:
        req = GetMessageResourceRequest.builder() \
            .message_id(message_id) \
            .file_key(file_key) \
            .type("file") \
            .build()
        resp = client.im.v1.message_resource.get(req)
        if not resp.success():
            print(f"下载文件失败: code={resp.code}, msg={resp.msg}")
            return ""
        with open(local_path, "wb") as f:
            f.write(resp.file.read())
        print(f"文件已下载: {local_path}")
        return local_path
    except Exception as e:
        print(f"download_file 异常: {e}")
        return ""


def cleanup_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
            print(f"临时文件已清理: {path}")
    except Exception as e:
        print(f"清理文件失败: {e}")
