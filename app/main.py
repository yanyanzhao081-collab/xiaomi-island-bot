from fastapi import FastAPI
from app.handlers import webhook

app = FastAPI(title="Xiaomi Island Bot")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "xiaomi-island-bot"}


# 保留 webhook 路由（兼容模式）
app.include_router(webhook.router, prefix="/webhook")
