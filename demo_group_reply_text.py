# -*- coding: utf-8 -*-
import asyncio
import os
import json
from aiohttp import web
import time
import aiohttp
from dotenv import load_dotenv

import botpy
from botpy import logging
from botpy.message import GroupMessage

# 加载 .env 文件
load_dotenv()

# 打印环境变量检查
print("BOT_APPID:", os.environ.get("BOT_APPID"))
print("BOT_SECRET:", os.environ.get("BOT_SECRET"))

# 从环境变量读取配置
config = {
    "appid": os.environ.get("BOT_APPID"),
    "secret": os.environ.get("BOT_SECRET"),
    "server_name": os.environ.get("SERVER_NAME", "GTNH 2.7.2"),
    "mc_server_url": os.environ.get("MC_SERVER_URL", "http://localhost:25555")
}

_log = logging.get_logger()

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

if __name__ == "__main__":
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents)
    client.run(appid=config["appid"], secret=config["secret"])