import os
import botpy
from botpy import logging
from botpy.message import GroupMessage
from botpy.ext import cog_yaml
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import aiohttp
import asyncio
import threading

_log = logging.get_logger()

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
    "server_name": os.environ.get("SERVER_NAME", "GTNH 2.7.2"),
    "mc_server_url": os.environ.get("MC_SERVER_URL", "http://localhost:25555")
}

class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"机器人 「{self.robot.name}」 已启动!")

    async def _send_message(self, message: GroupMessage, content: str):
        """统一的消息发送方法"""
        try:
            await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=0,
                msg_id=message.id,
                content=content
            )
            _log.info(f"成功发送到群 {message.group_openid}: {content}")
        except Exception as e:
            _log.error(f"发送消息失败: {e}")

    async def _fetch_server_status(self):
        """从MC服务器获取状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{config['mc_server_url']}/status") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception as e:
            _log.error(f"获取服务器状态失败: {e}")
            return None

    async def handle_server_status(self, message: GroupMessage):
        """处理/服务器人数命令"""
        status = await self._fetch_server_status()
        if status is None:
            response = f"[{config['server_name']}] 服务器当前可能已离线"
        else:
            response = (
                f"[{config['server_name']}] 在线人数: {status.get('onlineCount', 0)}\n"
                f"服务器已运行: {status.get('serverUptime', '未知')}\n"
                f"在线玩家详情: {status.get('details', '无')}"
            )
        await self._send_message(message, response)

    async def handle_daily_ranking(self, message: GroupMessage):
        """处理/在线排行命令"""
        status = await self._fetch_server_status()
        if status is None:
            response = f"[{config['server_name']}] 服务器当前可能已离线"
        else:
            response = f"[{config['server_name']}]\n{status.get('dailyRanking', '暂无排行数据')}"
        await self._send_message(message, response)

    async def on_group_at_message_create(self, message: GroupMessage):
        """处理所有@消息"""
        content = message.content
        if "/服务器人数" in content:
            await self.handle_server_status(message)
        elif "/在线排行" in content:
            await self.handle_daily_ranking(message)

def run_bot():
    """在新线程中运行机器人"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = MyClient(intents=botpy.Intents(public_messages=True))
    client.run(appid=config["appid"], secret=config["secret"])

@app.on_event("startup")
async def startup_event():
    """
    FastAPI 启动时触发，启动机器人
    """
    try:
        # 在新线程中启动机器人
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True  # 设置为守护线程
        bot_thread.start()
    except Exception as e:
        _log.error(f"机器人启动失败: {e}")
        raise

@app.get("/status")
async def get_status():
    """健康检查接口"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 