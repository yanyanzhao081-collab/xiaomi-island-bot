"""一次性脚本：通过飞书 API 自动创建多维表格「超级岛进度大盘」并添加字段"""

import json
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

# 从 .env 读取凭证
from dotenv import load_dotenv
import os

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()

# ── 第一步：创建多维表格应用 ──
print("正在创建多维表格...")

create_app_req = CreateAppRequest.builder() \
    .request_body(
        ReqApp.builder()
        .name("超级岛进度大盘")
        .folder_token("")
        .build()
    ) \
    .build()

create_app_resp = client.bitable.v1.app.create(create_app_req)

if not create_app_resp.success():
    print(f"创建多维表格失败: code={create_app_resp.code}, msg={create_app_resp.msg}")
    exit(1)

app_token = create_app_resp.data.app.app_token
print(f"✅ 多维表格创建成功! app_token = {app_token}")

# ── 第二步：获取默认数据表的 table_id ──
list_table_req = ListAppTableRequest.builder() \
    .app_token(app_token) \
    .build()

list_table_resp = client.bitable.v1.app_table.list(list_table_req)

if not list_table_resp.success():
    print(f"获取数据表列表失败: code={list_table_resp.code}, msg={list_table_resp.msg}")
    exit(1)

table_id = list_table_resp.data.items[0].table_id
print(f"✅ 默认数据表 table_id = {table_id}")

# ── 第三步：创建自定义字段 ──
fields = ["应用名称", "场景", "大岛", "小岛", "接入版本", "进度排期", "支持小窗", "支持分享"]

print("正在创建字段...")
for field_name in fields:
    create_field_req = CreateAppTableFieldRequest.builder() \
        .app_token(app_token) \
        .table_id(table_id) \
        .request_body(
            AppTableField.builder()
            .field_name(field_name)
            .type(1)  # 1 = 文本类型
            .build()
        ) \
        .build()

    create_field_resp = client.bitable.v1.app_table_field.create(create_field_req)
    if create_field_resp.success():
        print(f"  ✅ 字段 [{field_name}] 创建成功")
    else:
        print(f"  ❌ 字段 [{field_name}] 创建失败: {create_field_resp.msg}")

# ── 第四步：输出结果 ──
bitable_url = f"https://www.feishu.cn/base/{app_token}?table={table_id}"
print("\n" + "=" * 60)
print(f"BITABLE_APP_TOKEN={app_token}")
print(f"BITABLE_TABLE_ID={table_id}")
print(f"BITABLE_URL={bitable_url}")
print("=" * 60)
