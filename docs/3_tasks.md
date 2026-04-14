# 小米超级岛服务进度管家 — 任务拆解 (Task List)

## 任务总览

共 12 个任务（原 9 个 + 新增 3 个），已完成 11 个。

---

## Task 1：环境初始化与项目骨架搭建 ✅

- [x] 创建项目目录结构
- [x] 编写 `requirements.txt`
- [x] 创建 `.env.example`
- [x] 编写 `app/config.py`
- [x] 编写 `app/main.py`（含 /health 端点）
- [x] 编写 `README.md`

---

## Task 2：搭建 FastAPI 服务与飞书 Webhook 联调 ✅

- [x] 编写 `app/handlers/webhook.py`（url_verification + 消息接收）
- [x] 注册 `/webhook/event` 路由
- [x] 初始化 `larksuite-oapi` 客户端
- [x] 实现基础消息回复
- [x] 配置内网穿透（serveo）完成飞书联调

---

## Task 3：封装飞书多维表格 (Bitable) CRUD 工具类 ✅

- [x] 实现 `BitableService` 类（query_by_app_name, query_all, create_record, update_record, upsert_record, batch_create_records）
- [x] 通过脚本自动创建「超级岛进度大盘」多维表格及 8 个字段
- [x] 转让表格所有权给赵琰琰，机器人保留管理者权限
- [x] 统一异常处理

---

## Task 4：开发 LLM 意图识别模块 ✅

- [x] 编写 `app/services/llm.py`（LLMService 类）
- [x] 精心设计 System Prompt（意图分类 + 字段提取 + 应用名/场景拆分）
- [x] 编写 `app/handlers/llm_handler.py`（录入/查询/兜底三路分发）
- [x] 接入 webhook 路由

---

## Task 5：开发本地表格解析模块 ✅

- [x] 编写 `app/services/feishu_file.py`（文件下载服务）
- [x] 编写 `app/utils/field_mapper.py`（列名智能映射，含"是否支持小窗"等别名）
- [x] 编写 `app/handlers/file_handler.py`（解析 + 合并单元格 ffill + 批量写入）
- [x] 接入 webhook 文件消息路由

---

## Task 6：开发飞书表格链接解析模块 ✅（Sheets 待权限审批）

- [x] 编写 `app/utils/link_parser.py`（支持 Bitable + Sheets 链接，含 mi.feishu.cn 域名）
- [x] 编写 `app/services/feishu_sheet.py`（read_bitable + read_sheet，支持指定 sheet_id）
- [x] 编写 `app/handlers/link_handler.py`
- [x] 接入 webhook 链接路由
- [ ] 待 `sheets:spreadsheet:readonly` 权限审批通过后验证 Sheets 链接同步

---

## Task 7：开发飞书消息卡片模块 ✅

- [x] 对接人名单卡片（含邮箱：赵琰琰、白云鹏、汤德萍、张亚玲、赵巍）
- [x] 进度汇总卡片（统计概览 + Bitable 链接按钮）
- [x] 编写 `app/handlers/command_handler.py`

---

## Task 8：路由分发与整体流程串联 ✅

- [x] 在 `webhook.py` 中实现完整路由优先级：
  1. 文件消息 → file_handler
  2. 录入模板 → 提示
  3. 对接人 → 名单卡片
  4. 进度汇总 → 汇总卡片
  5. 飞书链接 → link_handler
  6. 其他文本 → LLM 意图识别
- [x] 端到端测试所有功能路径

---

## Task 9：整体测试与飞书权限申请清单整理 ✅

- [x] 整理飞书权限申请清单（见 docs/4_deployment_guide.md）
- [x] 整理事件订阅清单
- [x] 整理 Bitable 初始化步骤
- [x] 编写部署指南

---

## Task 10：录入权限控制（新增）✅

- [x] 在 `config.py` 中加载 `ADMIN_OPEN_IDS` 白名单
- [x] 在 `webhook.py` 中实现权限校验（_get_sender_open_id, _has_write_permission）
- [x] 写入操作（录入/文件/链接）需要权限，查询操作不限制
- [x] 无权限用户走只读模式（process_text_message_readonly）
- [ ] 待收集全部对接人 open_id 后配置白名单

---

## Task 11：双擎 LLM 容灾架构（新增）✅

- [x] 在 `.env` 和 `config.py` 中配置兜底模型（FALLBACK_LLM_*）
- [x] 重构 `LLMService.analyze()`：主力模型 8s 超时 → 自动降级到本地兜底模型
- [x] 抽取 `_call_llm()` 通用方法，复用 Prompt
- [ ] 待安装 Ollama 并拉取 qwen2.5:7b 后完成兜底测试

---

## Task 12：操作日志记录（新增）✅

- [x] 在 Bitable 中创建「操作日志」表（时间、用户ID、用户消息、机器人回复、操作类型）
- [x] 编写 `app/services/chat_log.py`（log_chat 函数）
- [x] 在 `llm_handler.py` 中接入日志记录（每次交互自动写入）
- [x] 在 `.env` 和 `config.py` 中配置 `BITABLE_LOG_TABLE_ID`

---

## 任务依赖关系

```
Task 1 (环境初始化) ✅
  └── Task 2 (Webhook 联调) ✅
        └── Task 3 (Bitable CRUD) ✅
              ├── Task 4 (LLM 意图识别) ✅
              ├── Task 5 (本地表格解析) ✅
              ├── Task 6 (飞书链接解析) ✅ (Sheets 待权限)
              ├── Task 7 (消息卡片) ✅
              ├── Task 10 (权限控制) ✅
              └── Task 12 (操作日志) ✅
                    └── Task 8 (路由串联) ✅
                          ├── Task 9 (测试与权限整理) ✅
                          └── Task 11 (双擎 LLM) ✅ (兜底待测试)
```
