"""一次性脚本：为 Bitable 添加协作者权限"""

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

# Bitable 在云文档体系中的 type 是 "bitable"
# 添加协作者使用 drive.v1.permission.member.create
# member_type: "email" 可以直接用邮箱添加

print("正在为 赵琰琰 (zhaoyanyan@xiaomi.com) 添加 Bitable 协作者权限...")

req = CreatePermissionMemberRequest.builder() \
    .token(BITABLE_APP_TOKEN) \
    .type("bitable") \
    .request_body(
        BaseMember.builder()
        .member_type("email")
        .member_id("zhaoyanyan@xiaomi.com")
        .perm("full_access")
        .build()
    ) \
    .build()

resp = client.drive.v1.permission_member.create(req)

if resp.success():
    print("✅ 权限添加成功! 赵琰琰 已获得「管理者」权限 (full_access)")
    print(f"   现在可以访问: https://www.feishu.cn/base/{BITABLE_APP_TOKEN}")
else:
    print(f"❌ 添加权限失败: code={resp.code}, msg={resp.msg}")
    print("   尝试其他方式...")
