from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import botpy
import os
from botpy.ext import cog_yaml

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 从环境变量获取配置
config = {
    "appid": os.environ.get("BOT_APPID"),
    "secret": os.environ.get("BOT_SECRET"),
    "target_group": os.environ.get("TARGET_GROUP"),
    "server_name": os.environ.get("SERVER_NAME", "GTNH 2.7.2"),
    "http_host": "0.0.0.0",
    "http_port": 8088,
    "mc_server_url": os.environ.get("MC_SERVER_URL", "http://localhost:25555")
}

@app.get("/status")
async def get_status():
    # 你的状态检查逻辑
    return {"status": "ok"}

@app.post("/message")
async def handle_message(message: dict):
    # 你的消息处理逻辑
    return {"success": True} 