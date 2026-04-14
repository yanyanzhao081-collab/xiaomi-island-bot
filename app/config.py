import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 飞书应用凭证
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_VERIFY_TOKEN = os.getenv("FEISHU_VERIFY_TOKEN", "")

    # 飞书 Bitable（底层数据库）
    BITABLE_APP_TOKEN = os.getenv("BITABLE_APP_TOKEN", "")
    BITABLE_TABLE_ID = os.getenv("BITABLE_TABLE_ID", "")
    BITABLE_LOG_TABLE_ID = os.getenv("BITABLE_LOG_TABLE_ID", "")
    BITABLE_URL = os.getenv("BITABLE_URL", "")

    # LLM
    LLM_API_BASE = os.getenv("LLM_API_BASE", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")

    # 录入权限白名单（open_id，逗号分隔）
    ADMIN_OPEN_IDS = os.getenv("ADMIN_OPEN_IDS", "")

    # 小米反馈平台
    XIAOMI_FEEDBACK_COOKIE = os.getenv("XIAOMI_FEEDBACK_COOKIE", "")

    # 兜底模型 (本地 Ollama)
    FALLBACK_LLM_API_BASE = os.getenv("FALLBACK_LLM_API_BASE", "http://localhost:11434/v1")
    FALLBACK_LLM_API_KEY = os.getenv("FALLBACK_LLM_API_KEY", "ollama")
    FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "qwen2.5:7b")
