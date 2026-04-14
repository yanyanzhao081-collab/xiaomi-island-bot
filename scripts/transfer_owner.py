"""一次性脚本：将 Bitable 所有权转让给赵琰琰，机器人降为管理者"""

import lark_oapi as lark
from lark_oapi.api.drive.v1 import *
from dotenv import load_dotenv
import os

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
BITABLE_APP_TOKEN = os.getenv("BITABLE_APP_TOKEN", "")

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

print("正在将 Bitable 所有权转让给 赵琰琰 (zhaoyanyan@xiaomi.com)...")

req = TransferOwnerPermissionMemberRequest.builder() \
    .token(BITABLE_APP_TOKEN) \
    .type("bitable") \
    .need_notification(True) \
    .old_owner_perm("full_access") \
    .request_body(
        Owner.builder()
        .member_type("email")
        .member_id("zhaoyanyan@xiaomi.com")
        .build()
    ) \
    .build()

resp = client.drive.v1.permission_member.transfer_owner(req)

if resp.success():
    print("✅ 所有权转让成功!")
    print("   赵琰琰 → 所有者")
    print("   小米超级岛服务进度管家 → 管理者 (full_access)")
else:
    print(f"❌ 转让失败: code={resp.code}, msg={resp.msg}")
