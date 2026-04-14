# 小米超级岛服务进度管家 — 技术设计文档

## 1. 技术栈总览

| 层级 | 技术选型 | 说明 |
|---|---|---|
| Web 框架 | Python 3.11+ / FastAPI / uvicorn | 异步高性能，适合 Webhook 场景 |
| 飞书 SDK | larksuite-oapi (v1.x) | 官方 Python SDK，覆盖消息、文件、Bitable 等 API |
| 文件处理 | pandas + openpyxl | Excel/CSV 解析与结构化处理 |
| LLM 智能层 | OpenAI 兼容接口 (httpx) | 双擎架构：主力线上模型 + 本地兜底模型 (Ollama) |
| 数据存储 | 飞书多维表格 (Bitable) | 进度数据表 + 操作日志表，Single Source of Truth |
| 配置管理 | python-dotenv | 环境变量管理 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      飞书客户端                           │
│  (群聊消息 / 文件上传 / 卡片交互 / 表格链接)               │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS Webhook
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   FastAPI 服务层                           │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Webhook     │  │  Card        │  │  Health        │  │
│  │  Handler     │  │  Callback    │  │  Check         │  │
│  │  /webhook    │  │  /callback   │  │  /health       │  │
│  └──────┬──────┘  └──────┬───────┘  └────────────────┘  │
│         │                │                               │
│         ▼                ▼                               │
│  ┌─────────────────────────────────────────────────┐     │
│  │              路由分发器 (Router)                   │     │
│  │  1. 文件消息 → FileHandler                       │     │
│  │  2. 精确指令 → CommandHandler                    │     │
│  │  3. 飞书链接 → LinkHandler                       │     │
│  │  4. 其他文本 → LLMHandler                        │     │
│  └──────┬──────────┬──────────┬──────────┬─────────┘     │
│         │          │          │          │               │
│         ▼          ▼          ▼          ▼               │
│  ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│  │ File     │ │Command │ │ Link   │ │ LLM    │         │
│  │ Handler  │ │Handler │ │Handler │ │Handler │         │
│  └────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘         │
│       │            │          │          │               │
└───────┼────────────┼──────────┼──────────┼───────────────┘
        │            │          │          │
        ▼            ▼          ▼          ▼
┌──────────────────────────────────────────────────────────┐
│                    核心服务层                              │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Bitable     │  │  LLM         │  │  Card         │  │
│  │  Service     │  │  Service     │  │  Builder      │  │
│  │  (CRUD)      │  │  (NLP)       │  │  (消息卡片)    │  │
│  └──────┬───────┘  └──────────────┘  └───────────────┘  │
│         │                                                │
└─────────┼────────────────────────────────────────────────┘
          │ Bitable API
          ▼
┌──────────────────────────────────────────────────────────┐
│              飞书多维表格 (Bitable)                        │
│              — Single Source of Truth —                   │
│                                                          │
│  进度数据表：应用名称 | 场景 | 大岛 | 小岛 | 接入版本     │
│             | 进度排期 | 支持小窗 | 支持分享               │
│  操作日志表：时间 | 用户ID | 用户消息 | 机器人回复         │
│             | 操作类型                                     │
└──────────────────────────────────────────────────────────┘
```

---

## 3. 项目目录结构

```
xiaomi-island-bot/
├── docs/                          # 文档
│   ├── 1_product_requirements.md
│   ├── 2_technical_design.md
│   ├── 3_tasks.md
│   └── 4_deployment_guide.md      # 部署与权限指南
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口，注册路由
│   ├── config.py                  # 环境变量与配置加载（含双擎LLM、权限白名单）
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── webhook.py             # 飞书 Webhook 事件处理 + 路由分发 + 权限校验
│   │   ├── file_handler.py        # 本地文件（Excel/CSV）解析（含合并单元格处理）
│   │   ├── link_handler.py        # 飞书表格链接解析（Bitable + Sheets）
│   │   ├── command_handler.py     # 精确指令处理（对接人/汇总）
│   │   └── llm_handler.py         # LLM 意图识别与文本录入/查询
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bitable.py             # Bitable CRUD 封装（进度数据表）
│   │   ├── llm.py                 # 双擎 LLM 服务（主力 + 兜底）
│   │   ├── feishu_file.py         # 飞书文件下载服务
│   │   ├── feishu_sheet.py        # 飞书电子表格/Bitable 读取服务
│   │   └── chat_log.py            # 操作日志记录服务
│   ├── cards/
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── field_mapper.py        # 表格列名 → 标准字段映射
│       └── link_parser.py         # 飞书链接正则解析
├── scripts/                       # 一次性运维脚本
│   ├── create_bitable.py          # 创建多维表格
│   ├── add_collaborator.py        # 添加协作者
│   └── transfer_owner.py          # 转让所有权
├── tests/
│   └── __init__.py
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
└── README.md
```

---

## 4. 核心模块设计

### 4.1 飞书 Webhook 处理 (`handlers/webhook.py`)

**职责**：接收飞书事件回调，完成验证后分发到路由器。

**关键逻辑**：

1. 接收 POST 请求，解析飞书事件体。
2. 处理 `url_verification` 挑战（首次配置 Webhook 时飞书会发送验证请求）。
3. 对 `im.message.receive_v1` 事件进行去重（基于 `event_id`，防止重复处理）。
4. 提取消息类型 (`msg_type`) 和消息内容，传递给路由分发器。

**去重机制**：

```python
# 使用内存 set + TTL 进行事件去重
# 生产环境可替换为 Redis
processed_events: dict[str, float] = {}  # event_id -> timestamp
EVENT_TTL = 300  # 5 分钟过期
```

### 4.2 路由分发器 (`router.py`)

**职责**：根据消息类型和内容，将请求分发到对应的 Handler。

**路由判定逻辑（伪代码）**：

```python
async def dispatch(message: Message) -> None:
    # 1. 文件消息
    if message.msg_type == "file":
        await file_handler.handle(message)
        return

    text = message.content.strip()

    # 2. 精确指令匹配
    if text in ("录入模板", "模板"):
        await command_handler.send_template_card(message)
        return
    if text == "对接人":
        await command_handler.send_contact_card(message)
        return
    if text in ("进度汇总", "汇总"):
        await command_handler.send_summary(message)
        return

    # 3. 飞书表格链接检测
    if link_parser.contains_feishu_link(text):
        await link_handler.handle(message)
        return

    # 4. 兜底：LLM 意图识别
    await llm_handler.handle(message)
```

### 4.3 Bitable CRUD 服务 (`services/bitable.py`)

**职责**：封装飞书多维表格的增删改查操作，作为机器人的数据库层。

**核心接口**：

```python
class BitableService:
    def __init__(self, app_token: str, table_id: str):
        """初始化，绑定目标 Bitable 表格"""

    async def query_by_app_name(self, app_name: str) -> Optional[dict]:
        """根据应用名称查询单条记录"""

    async def query_all(self) -> list[dict]:
        """查询全部记录"""

    async def create_record(self, fields: dict) -> str:
        """新增一条记录，返回 record_id"""

    async def update_record(self, record_id: str, fields: dict) -> None:
        """更新指定记录"""

    async def upsert_record(self, app_name: str, fields: dict) -> str:
        """智能插入或更新：存在则更新，不存在则新增"""

    async def batch_create_records(self, records: list[dict]) -> dict:
        """批量新增记录，返回成功/失败统计"""
```

**飞书 Bitable API 调用要点**：

- 使用 `larksuite-oapi` 的 `client.bitable.v1.app_table_record` 系列方法。
- 查询使用 `filter` 参数按应用名称精确匹配。
- 批量写入使用 `batch_create` 接口，单次最多 500 条。
- 所有操作需要 `bitable:app` 权限范围。

### 4.4 LLM 意图识别服务 (`services/llm.py`)

**职责**：双擎架构 LLM 服务，主力线上模型 + 本地兜底模型，进行意图分类和字段提取。

**双擎降级逻辑**：

```
用户输入
    │
    ▼
主力模型（Kimi/Moonshot，timeout=8s）
    │
    ├── 成功 → 返回结果
    │
    └── 失败/超时 → 打印警告日志
                      │
                      ▼
              兜底模型（本地 Ollama qwen2.5:7b，timeout=30s）
                      │
                      ├── 成功 → 返回结果
                      └── 失败 → 返回 {"intent": "unknown"}
```

**意图分类**：

| 意图 | 说明 | 示例 |
|---|---|---|
| `record` | 录入或更新进度 | "拼多多预计26.4接入" |
| `query` | 查询某应用进度 | "查一下拼多多的进度" |
| `unknown` | 无法识别 | "今天天气怎么样" |

**字段提取增强规则**：

- "京东外卖" → app_name="京东"，scene="外卖"（应用名与场景自动拆分）
- "有大岛"、"支持小窗" → 填 "✅"
- "大岛购物" → 填具体分类名"购物"
- 未提及的字段 → 空字符串

**调用方式**：

- 使用 `httpx.AsyncClient` 调用 OpenAI 兼容接口。
- 设置 `response_format: { type: "json_object" }` 确保返回 JSON。
- 主力模型超时 8 秒，兜底模型超时 30 秒。

### 4.5 文件处理模块 (`handlers/file_handler.py`)

**职责**：处理用户上传的 Excel/CSV 文件，解析后批量写入 Bitable。

**处理流程**：

```
文件消息 → 获取 file_key → 下载文件 → 判断格式
    ├── .xlsx → pandas.read_excel(engine='openpyxl')
    └── .csv  → pandas.read_csv()
→ 合并单元格处理 (ffill) → 列名映射 (field_mapper) → 数据校验 → 批量写入 Bitable → 回复结果卡片 → 清理临时文件
```

**文件下载**：

- 通过飞书 `im.v1.message.resource` API 获取文件内容。
- 保存到 `/tmp/island_bot/` 临时目录。
- 处理完成后立即删除。

**列名映射 (`utils/field_mapper.py`)**：

```python
COLUMN_ALIASES = {
    "应用名称": ["app", "应用", "应用名", "名称", "app_name"],
    "场景": ["scene", "场景", "接入场景"],
    "大岛": ["big_island", "一级分类", "大岛"],
    "小岛": ["small_island", "二级分类", "小岛"],
    "接入版本": ["version", "版本", "接入版本"],
    "进度排期": ["schedule", "进度", "排期", "时间"],
    "支持小窗": ["mini_window", "小窗", "支持小窗"],
    "支持分享": ["share", "分享", "支持分享"],
}

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将 DataFrame 的列名映射为标准字段名"""
```

### 4.6 飞书表格链接解析 (`handlers/link_handler.py`)

**职责**：识别消息中的飞书表格链接，读取源表数据并同步到目标 Bitable。

**链接正则**：

```python
BITABLE_PATTERN = r'https?://[\w.-]+\.feishu\.cn/base/([\w]+)(?:\?table=([\w]+))?'
SHEET_PATTERN = r'https?://[\w.-]+\.feishu\.cn/sheets/([\w]+)'
```

**处理流程**：

```
消息文本 → 正则提取链接 → 判断类型
    ├── Bitable 链接 → 调用 Bitable API 读取源表记录
    └── Sheets 链接  → 调用 Sheets API 读取电子表格数据
→ 列名映射 → 数据校验 → 批量写入目标 Bitable → 回复结果卡片
```

### 4.7 消息卡片构建 (`cards/`)

所有卡片使用飞书 Message Card JSON 协议构建。

**录入模板卡片 (`template_card.py`)**：

- 使用 `form` 组件，包含文本输入和下拉选择。
- 提交按钮触发 card callback。

**进度汇总卡片 (`summary_card.py`)**：

- 顶部：统计概览（总数、各场景分布）。
- 中部：进度状态分布。
- 底部：可点击的 Bitable 链接按钮。
  ```
  链接格式：https://{domain}.feishu.cn/base/{app_token}?table={table_id}
  ```

**对接人卡片 (`contact_card.py`)**：

- 固定内容，展示四位对接人的角色和姓名。

---

## 5. 数据流转架构

### 5.1 写入流（录入/更新）

```
用户输入 (文本/文件/卡片/链接)
    │
    ▼
路由分发 → Handler 处理 → 结构化数据
    │
    ▼
BitableService.upsert_record() / batch_create_records()
    │
    ▼
飞书 Bitable API → 数据落盘
    │
    ▼
回复确认卡片
```

### 5.2 读取流（查询/汇总）

```
用户查询指令
    │
    ▼
路由分发 → Handler 处理
    │
    ▼
BitableService.query_by_app_name() / query_all()
    │
    ▼
飞书 Bitable API → 返回数据
    │
    ▼
CardBuilder 构建卡片 → 回复用户
    │
    ▼
（汇总场景）附带 Bitable 在线链接
```

---

## 6. 飞书 API 权限清单

机器人需要申请以下飞书应用权限：

| 权限标识 | 权限名称 | 用途 |
|---|---|---|
| `im:message` | 获取与发送单聊、群组消息 | 接收用户消息、发送回复 |
| `im:message.group_at_msg` | 接收群聊中 @ 机器人消息 | 群聊场景触发 |
| `im:resource` | 获取消息中的资源文件 | 下载用户上传的 Excel/CSV 文件 |
| `bitable:app` | 查看、评论、编辑和管理多维表格 | Bitable CRUD 操作 |
| `sheets:spreadsheet` | 查看、评论、编辑和管理电子表格 | 读取飞书电子表格链接中的数据 |
| `contact:user.id:readonly` | 获取用户 user_id | 识别消息发送者 |

**事件订阅**：

| 事件 | 说明 |
|---|---|
| `im.message.receive_v1` | 接收消息事件 |
| `card.action.trigger` | 卡片交互回调事件 |

---

## 7. 环境变量配置

```env
# 飞书应用凭证
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx

# 飞书 Bitable 配置（机器人的底层数据库）
BITABLE_APP_TOKEN=bascnXXXXXXXXXX
BITABLE_TABLE_ID=tblXXXXXXXXXX

# Bitable 在线访问链接（用于汇总时分享）
BITABLE_URL=https://xxx.feishu.cn/base/bascnXXXXXXXXXX?table=tblXXXXXXXXXX

# LLM 配置（OpenAI 兼容接口）
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini

# 兜底模型（本地 Ollama）
FALLBACK_LLM_API_BASE=http://localhost:11434/v1
FALLBACK_LLM_API_KEY=ollama
FALLBACK_LLM_MODEL=qwen2.5:7b

# 录入权限白名单（open_id，逗号分隔，为空则所有人可录入）
ADMIN_OPEN_IDS=ou_xxx1,ou_xxx2

# Bitable 操作日志表
BITABLE_LOG_TABLE_ID=tblXXXXXXXXXX

# 服务配置
HOST=0.0.0.0
PORT=8000
```

---

## 8. 关键设计决策

### 8.1 为什么选择 Bitable 作为数据库？

- **零运维**：无需部署和维护独立数据库。
- **天然可视化**：Bitable 本身就是一个在线表格，用户可直接打开查看、筛选、导出。
- **权限复用**：飞书的权限体系天然支持团队协作。
- **满足"进度汇总"需求**：直接分享 Bitable 链接即可，无需额外生成报表。

### 8.2 表格数据为什么不过 LLM？

- 表格数据已经是结构化的，直接进行列名映射即可。
- 过 LLM 会增加延迟和成本，且对结构化数据没有额外价值。
- LLM 仅用于非结构化的自然语言文本场景。

### 8.3 卡片回调的安全性

- 飞书卡片回调会携带签名，需在 callback handler 中进行验签。
- 使用飞书 SDK 内置的验签方法，确保请求来源合法。
