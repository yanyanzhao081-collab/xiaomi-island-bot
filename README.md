# 小米超级岛服务进度管家

飞书群聊机器人，用于管理和查询各应用接入超级岛、负一屏小部件的开发进度。

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入真实的飞书凭证和 LLM 配置
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 验证

```bash
curl http://localhost:8000/health
```

预期返回：`{"status":"ok","service":"xiaomi-island-bot"}`

## 项目结构

```
app/
├── main.py          # FastAPI 入口
├── config.py        # 环境变量配置
├── router.py        # 消息路由分发
├── handlers/        # 各类消息处理器
├── services/        # 核心服务（Bitable、LLM、文件等）
├── cards/           # 飞书消息卡片模板
└── utils/           # 工具函数
```

## 文档

- [产品需求文档](docs/1_product_requirements.md)
- [技术设计文档](docs/2_technical_design.md)
- [任务拆解](docs/3_tasks.md)
