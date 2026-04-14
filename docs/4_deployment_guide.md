# 小米超级岛服务进度管家 — 部署与权限指南

## 1. 飞书权限申请清单

### 应用权限（API Scopes）

| 权限标识 | 权限名称 | 用途 | 状态 |
|---|---|---|---|
| `im:message` | 获取与发送单聊、群组消息 | 接收用户消息、发送回复 | ✅ 已开通 |
| `im:message.group_at_msg` | 接收群聊中 @机器人消息 | 群聊场景触发 | ✅ 已开通 |
| `im:resource` | 获取消息中的资源文件 | 下载用户上传的 Excel/CSV 文件 | ✅ 已开通 |
| `bitable:app` | 多维表格读写 | Bitable CRUD（底层数据库） | ✅ 已开通 |
| `drive:drive:readonly` | 云文档只读 | 读取飞书表格链接中的数据 | ✅ 已开通 |
| `sheets:spreadsheet:readonly` | 电子表格只读 | 读取飞书 Sheets 链接 | ⏳ 已申请 |
| `contact:user.id:readonly` | 获取用户 ID | 权限白名单校验 | ⏳ 待申请 |

### 事件订阅

| 事件 | 说明 |
|---|---|
| `im.message.receive_v1` | 接收消息事件（文本、文件等） |

### 订阅方式
- 将事件发送至开发者服务器
- Webhook URL: `https://<公网地址>/webhook/event`

---

## 2. 环境变量配置 (.env)

```env
# 飞书应用凭证
FEISHU_APP_ID=cli_a92d5f05713a9bc8
FEISHU_APP_SECRET=<your_secret>
FEISHU_VERIFY_TOKEN=<your_verify_token>

# 飞书 Bitable（底层数据库）
BITABLE_APP_TOKEN=ZexWb1T0PaiAvfsJRMucHNZ8nKb
BITABLE_TABLE_ID=tblMq10EmM9tyvWp
BITABLE_URL=https://www.feishu.cn/base/ZexWb1T0PaiAvfsJRMucHNZ8nKb?table=tblMq10EmM9tyvWp

# LLM（Kimi / Moonshot）
LLM_API_BASE=https://api.moonshot.cn/v1
LLM_API_KEY=<your_api_key>
LLM_MODEL=moonshot-v1-8k

# 录入权限白名单（open_id，逗号分隔，为空则所有人可录入）
ADMIN_OPEN_IDS=ou_3f99be715bb36e3d856038377d710c9c

# 服务
HOST=127.0.0.1
PORT=9000
```

---

## 3. Bitable 初始化（已完成）

- ✅ 多维表格「超级岛进度大盘」已创建
- ✅ 字段已配置：应用名称、场景、大岛、小岛、接入版本、进度排期、支持小窗、支持分享
- ✅ app_token = `ZexWb1T0PaiAvfsJRMucHNZ8nKb`
- ✅ table_id = `tblMq10EmM9tyvWp`
- ✅ 所有权已转让给赵琰琰，机器人为管理者

---

## 4. 部署方式

### 方式一：直接运行（开发环境）

```bash
pip install -r requirements.txt
cp .env.example .env  # 填入真实配置
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### 方式二：Docker 部署（生产环境）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
```

```bash
docker build -t island-bot .
docker run -d --env-file .env -p 9000:9000 island-bot
```

### 内网穿透（开发调试）

```bash
ssh -o StrictHostKeyChecking=no -R 80:localhost:9000 serveo.net
```

---

## 5. 功能验收清单

| 功能 | 触发方式 | 状态 |
|---|---|---|
| NLP 智能录入 | 发送自然语言（如"拼多多预计26.4接入"） | ✅ |
| NLP 查询 | 发送"查一下拼多多的进度" | ✅ |
| 本地 Excel 批量录入 | 上传 .xlsx / .csv 文件 | ✅ |
| 飞书 Bitable 链接同步 | 发送 Bitable 链接 | ✅ |
| 飞书 Sheets 链接同步 | 发送 Sheets 链接 | ⏳ 待权限审批 |
| 对接人名单 | 发送"对接人" | ✅ |
| 进度汇总 + 表格链接 | 发送"进度汇总" | ✅ |
| 录入权限控制 | 白名单外用户尝试录入 | ✅ 代码就绪 |

---

## 6. 对接人名单

| 角色 | 姓名 | 邮箱 |
|---|---|---|
| 岛运营 | 赵琰琰 | zhaoyanyan@xiaomi.com |
| 岛运营 | 白云鹏 | v-baiyunpeng5@xiaomi.com |
| mipush 运营 | 汤德萍 | v-tangdeping@xiaomi.com |
| 岛产品 | 张亚玲 | zhangyaling1@xiaomi.com |
| 岛后台产品 | 赵巍 | zhaowei45@xiaomi.com |
