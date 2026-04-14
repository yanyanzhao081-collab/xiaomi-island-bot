"""LLM 意图识别与字段提取服务"""

import json
import httpx
from app.config import Config

SYSTEM_PROMPT = """你是「小米超级岛服务进度管家」的智能助手。你的任务是分析用户输入，判断意图并提取结构化字段。

## 意图分类规则
- "record"：用户想要录入或更新某个应用的接入进度。关键词包括：接入、预计、版本、排期、开发中、测试中、已上线、完成、支持等。
- "query"：用户想要查询某个应用或某个场景的进度。关键词包括：查、查一下、进度、什么情况、怎么样、有哪些、分别是什么、列表等。
  - 如果用户问的是某个具体应用（如"查一下拼多多"），提取 app_name。
  - 如果用户问的是某个场景/类别（如"打车的有哪些"、"外卖的12个分别是什么"），提取 scene。
  - 两者都有也可以同时提取。
- "delete"：用户想要删除某条记录。关键词包括：删除、删掉、移除、去掉等。需要提取 app_name，如果有 scene 也提取。
- "unknown"：无法归类为以上三种的闲聊或无关内容。

## 字段提取规则（仅当 intent 为 "record" 或 "query" 时提取）

### app_name（应用名称）
纯粹的应用/公司名称，不包含业务类型后缀。
例如"京东外卖"要拆分为：app_name="京东"，scene="外卖"。
例如"美团打车"要拆分为：app_name="美团"，scene="打车"。
例如"拼多多"没有业务后缀，app_name="拼多多"。
示例：京东、美团、拼多多、抖音、小红书、饿了么

### scene（场景）
应用接入的业务场景或服务类型。
- 如果用户说"京东外卖"，场景="外卖"
- 如果用户说"美团打车"，场景="打车"
- 如果用户说"接入超级岛"，场景="超级岛"
- 如果用户说"负一屏小部件"，场景="负一屏小部件"
- 可以是任意业务类型：外卖、打车、购物、音乐、视频、超级岛、负一屏小部件等
- 未提及则为空字符串

### big_island（大岛）
是否支持大岛卡片。
- 如果用户说"有大岛"、"支持大岛"、"大岛已完成"等肯定表述 → 填 "✅"
- 如果用户说"无大岛"、"不支持大岛" → 填 "❌"
- 如果用户在大岛后面跟了具体分类名（如"大岛购物"）→ 填该分类名
- 如果未提及 → 填 "DEFAULT"（系统会自动设为 ✅）

### small_island（小岛）
是否支持小岛卡片。规则同大岛：
- 肯定表述 → "✅"
- 否定表述 → "❌"
- 具体分类名 → 填分类名
- 未提及 → "DEFAULT"（系统会自动设为 ✅）

### version（接入版本）
计划接入的系统版本号，如：26.4、27.0。未提及则为空。

### schedule（进度排期）
当前进度或预计完成时间。如：开发中、测试中、已上线、4月17号、2026-04-15。未提及则为空。

### support_mini_window（支持小窗）
是否支持小窗模式。
- 肯定表述（"支持小窗"、"有小窗"） → "✅"
- 否定表述（"不支持小窗"、"无小窗"） → "❌"
- **未提及 → 空字符串（绝对不要猜测，必须留空）**

### support_share（支持分享）
是否支持分享功能。
- 肯定表述（"支持分享"、"有分享"） → "✅"
- 否定表述（"不支持分享"） → "❌"
- **未提及 → 空字符串（绝对不要猜测，必须留空）**

## 示例

用户输入："京东外卖，预计4月17号接入，有大岛，小岛支持分享"
输出：
{
  "intent": "record",
  "fields": {
    "app_name": "京东",
    "scene": "外卖",
    "big_island": "✅",
    "small_island": "✅",
    "version": "",
    "schedule": "4月17号",
    "support_mini_window": "",
    "support_share": "✅"
  }
}

用户输入："拼多多预计26.4接入超级岛，大岛购物"
注意："大岛购物"表示大岛的分类是购物，不是"有大岛"。如果用户在大岛/小岛后面跟了具体分类名（如购物、出行、娱乐、外卖），则填写该分类名而非 ✅。
输出：
{
  "intent": "record",
  "fields": {
    "app_name": "拼多多",
    "scene": "超级岛",
    "big_island": "购物",
    "small_island": "",
    "version": "26.4",
    "schedule": "",
    "support_mini_window": "",
    "support_share": ""
  }
}

## 输出格式
必须返回严格的 JSON，不要包含任何其他文字：
{
  "intent": "record" | "query" | "delete" | "unknown",
  "fields": {
    "app_name": "",
    "scene": "",
    "big_island": "",
    "small_island": "",
    "version": "",
    "schedule": "",
    "support_mini_window": "",
    "support_share": ""
  }
}

当 intent 为 "unknown" 时，fields 中所有值为空字符串。"""


# 字段映射：LLM 输出 key → Bitable 列名
FIELD_MAP = {
    "app_name": "应用名称",
    "scene": "场景",
    "big_island": "大岛",
    "small_island": "小岛",
    "version": "接入版本",
    "schedule": "进度排期",
    "support_mini_window": "支持小窗",
    "support_share": "支持分享",
}


class LLMService:
    """双擎架构：主力模型 + 本地兜底模型"""

    def __init__(self):
        # 主力模型
        self.primary_base = Config.LLM_API_BASE.rstrip("/")
        self.primary_key = Config.LLM_API_KEY
        self.primary_model = Config.LLM_MODEL
        # 兜底模型
        self.fallback_base = Config.FALLBACK_LLM_API_BASE.rstrip("/")
        self.fallback_key = Config.FALLBACK_LLM_API_KEY
        self.fallback_model = Config.FALLBACK_LLM_MODEL

    async def _call_llm(self, api_base: str, api_key: str, model: str, text: str, timeout: float) -> dict:
        """调用单个 LLM，返回解析后的 dict"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

    async def analyze(self, text: str) -> dict:
        """分析用户输入，主力模型优先，失败自动降级到本地兜底模型"""

        # ── 第一步：尝试主力模型 ──
        try:
            print(f"[LLM] 调用主力模型: {self.primary_model}")
            result = await self._call_llm(
                self.primary_base, self.primary_key, self.primary_model, text, timeout=8.0
            )
            print(f"[LLM] 主力模型返回成功: intent={result.get('intent')}")
            return self._ensure_structure(result)

        except Exception as e:
            print(f"⚠️ 主力大模型请求失败或超时，正在切换至本地兜底模型... 错误: {e}")

        # ── 第二步：降级到兜底模型 ──
        try:
            print(f"[LLM] 调用兜底模型: {self.fallback_model}")
            result = await self._call_llm(
                self.fallback_base, self.fallback_key, self.fallback_model, text, timeout=30.0
            )
            print(f"[LLM] 兜底模型返回成功: intent={result.get('intent')}")
            return self._ensure_structure(result)

        except Exception as e:
            print(f"❌ 兜底模型也失败了: {e}")
            return {"intent": "unknown", "fields": {}}

    def _ensure_structure(self, result: dict) -> dict:
        """确保返回结构完整"""
        if "intent" not in result:
            result["intent"] = "unknown"
        if "fields" not in result:
            result["fields"] = {}
        return result

    def map_fields_to_bitable(self, fields: dict) -> dict:
        """将 LLM 输出的英文 key 映射为 Bitable 中文列名，处理默认值"""
        mapped = {}
        for eng_key, cn_name in FIELD_MAP.items():
            value = fields.get(eng_key, "")
            # 大岛/小岛：未提及时默认 ✅
            if eng_key in ("big_island", "small_island") and (value == "DEFAULT" or value == ""):
                mapped[cn_name] = "✅"
            # 小窗/分享：未提及时默认 ❌
            elif eng_key in ("support_mini_window", "support_share") and value == "":
                mapped[cn_name] = "❌"
            elif value and value != "DEFAULT":
                mapped[cn_name] = value
        return mapped


llm_service = LLMService()
