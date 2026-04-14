"""独立运行飞书长连接客户端（不依赖 uvicorn）"""

from app.ws_client import start_ws_client

if __name__ == "__main__":
    start_ws_client()
