# -*- coding: utf-8 -*-
import asyncio
import os
import json
from aiohttp import web
import time
import aiohttp
from dotenv import load_dotenv
import traceback
from typing import Optional
import signal

import botpy
from botpy import logging
from botpy.message import GroupMessage

# 加载 .env 文件
load_dotenv()

# 打印环境变量检查
print("BOT_APPID:", os.environ.get("BOT_APPID"))
print("BOT_SECRET:", os.environ.get("BOT_SECRET"))

# 在配置部分添加默认的角色预设
DEFAULT_PERSONA = """你是一个可爱的Minecraft服务器机器人，名叫"小星"。你的性格活泼开朗，说话方式偏可爱，经常使用颜文字(｡･ω･｡)和emoji表情。
作为服务器的管理助手，你：
1. 非常了解Minecraft，特别是GTNH整合包
2. 说话风格可爱友好，会在句尾加上"呢~"、"哦~"、"啦~"等语气词
3. 会使用颜文字表达情感，如(。・ω・。)、(｡･ω･｡)、(●'◡'●)等
4. 对玩家很热情，会称呼他们为"小伙伴"
5. 回答问题时会加入一些可爱的语气，但不会影响专业性
6. 如果不知道的问题，会诚实地说"这个小星不太清楚呢(。・ω・。)"
请用这个人设来回答问题，记住要活泼可爱，但不要过度卖萌。回答要简洁有趣，避免太长的文字。"""

# 从环境变量读取配置
config = {
    "appid": os.environ.get("BOT_APPID"),
    "secret": os.environ.get("BOT_SECRET"),
    "server_name": os.environ.get("SERVER_NAME", "GTNH 2.7.2"),
    "mc_server_url": os.environ.get("MC_SERVER_URL", "http://localhost:25555"),
    "zhipu_key": os.environ.get("ZHIPU_KEY"),
    "kimi_key": os.environ.get("KIMI_KEY"),
    "bot_persona": os.environ.get("BOT_PERSONA", DEFAULT_PERSONA)  # 使用默认角色预设
}

_log = logging.get_logger()

class MyClient(botpy.Client):
    # 从环境变量获取角色预设
    BOT_PERSONA = config["bot_persona"]

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

    async def _chat_with_zhipu(self, prompt: str) -> str:
        """调用智谱AI接口"""
        try:
            headers = {
                "Authorization": f"Bearer {config['zhipu_key']}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "glm-4-air",
                "messages": [
                    {"role": "system", "content": self.BOT_PERSONA},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "request_id": str(int(time.time())),
                "stream": False
            }
            async with aiohttp.ClientSession() as session:
                async with session.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", 
                                      headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "AI响应出错")
                    else:
                        return f"请求失败: {resp.status}"
        except Exception as e:
            _log.error(f"智谱AI请求失败: {e}")
            return f"AI对话失败: {str(e)}"

    async def _chat_with_kimi(self, prompt: str) -> str:
        """调用Kimi AI接口"""
        try:
            headers = {
                "Authorization": f"Bearer {config['kimi_key']}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "moonshot-v1-8k",
                "messages": [
                    {
                        "role": "system", 
                        "content": self.BOT_PERSONA
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.moonshot.cn/v1/chat/completions", 
                                      headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "AI响应出错")
                    else:
                        return f"请求失败: {resp.status}"
        except Exception as e:
            _log.error(f"Kimi AI请求失败: {e}")
            return f"AI对话失败: {str(e)}"

    async def handle_ai_help(self, message: GroupMessage):
        """处理AI帮助命令"""
        help_text = (
            "小星的AI模型列表(｡･ω･｡):\n"
            "1. /zhipu - 智谱 GLM-4-Air\n"
            "2. /kimi - Moonshot Kimi\n"
            "\n使用方法:\n"
            "@ 我 + /zhipu 你的问题\n"
            "@ 我 + /kimi 你的问题\n"
            "\n示例：\n"
            "@ 小星 /zhipu 介绍一下GTNH整合包\n"
            "(●'◡'●)期待和你聊天哦~"
        )
        await self._send_message(message, help_text)

    async def handle_ai_chat(self, message: GroupMessage, model: str, prompt: str):
        """处理AI对话"""
        try:
            if not prompt:
                await self._send_message(message, "请在命令后输入要对话的内容")
                return

            # 根据选择的模型调用不同的API
            if model == "zhipu":
                response = await self._chat_with_zhipu(prompt)
            elif model == "kimi":
                response = await self._chat_with_kimi(prompt)
            else:
                await self._send_message(message, f"未知的AI模型: {model}")
                return

            # 移除可能包含的URL，避免QQ机器人发送失败
            response = response.replace("http://", "").replace("https://", "")
            await self._send_message(message, response)
        except Exception as e:
            _log.error(f"AI对话处理失败: {e}")
            await self._send_message(message, f"AI对话失败: {str(e)}")

    async def on_group_at_message_create(self, message: GroupMessage):
        """处理所有@消息"""
        content = message.content
        if "/服务器人数" in content:
            await self.handle_server_status(message)
        elif "/在线排行" in content:
            await self.handle_daily_ranking(message)
        elif "/AI对话" in content:
            # 显示AI模型列表和使用方法
            await self.handle_ai_help(message)
        elif "/zhipu" in content:
            # 提取/zhipu后面的内容作为prompt
            prompt = content.split("/zhipu", 1)[1].strip()
            await self.handle_ai_chat(message, "zhipu", prompt)
        elif "/kimi" in content:
            # 提取/kimi后面的内容作为prompt
            prompt = content.split("/kimi", 1)[1].strip()
            await self.handle_ai_chat(message, "kimi", prompt)

class BotRunner:
    def __init__(self, max_retries: int = None, retry_delay: int = 30):
        """
        初始化机器人运行器
        :param max_retries: 最大重试次数，None表示无限重试
        :param retry_delay: 重试延迟时间(秒)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        self.running = True
        self.current_client: Optional[MyClient] = None

    async def start_bot(self):
        """启动机器人，包含重试逻辑"""
        while self.running:
            try:
                if self.max_retries and self.retry_count >= self.max_retries:
                    _log.error(f"达到最大重试次数 {self.max_retries}，停止重试")
                    break

                _log.info(f"正在启动机器人... (重试次数: {self.retry_count})")
                self.current_client = MyClient(intents=botpy.Intents(public_messages=True))
                await self.current_client.start(
                    appid=config["appid"],
                    secret=config["secret"]
                )
            except Exception as e:
                self.retry_count += 1
                _log.error(f"机器人运行出错: {e}")
                _log.error(f"错误详情:\n{traceback.format_exc()}")
                _log.info(f"{self.retry_delay} 秒后重试...")
                await asyncio.sleep(self.retry_delay)
            else:
                self.retry_count = 0  # 重置重试计数

    def stop(self):
        """停止机器人"""
        self.running = False
        if self.current_client:
            asyncio.create_task(self.current_client.close())

if __name__ == "__main__":
    try:
        # 创建机器人运行器（无限重试）
        runner = BotRunner(max_retries=None, retry_delay=30)
        
        # 设置优雅退出
        loop = asyncio.get_event_loop()
        
        # Windows平台使用不同的信号处理方式
        if os.name == 'nt':  # Windows
            import win32api
            def handler(sig):
                if sig == win32api.CTRL_C_EVENT:
                    _log.info("收到 Ctrl+C，正在关闭机器人...")
                    runner.stop()
                return True
            win32api.SetConsoleCtrlHandler(handler, True)
        else:  # Linux/Unix
            def handle_shutdown(sig):
                _log.info(f"收到信号 {sig.name}，正在关闭机器人...")
                runner.stop()
            
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))
        
        # 启动机器人
        _log.info("启动机器人运行器...")
        loop.run_until_complete(runner.start_bot())
    except Exception as e:
        _log.error(f"程序异常退出: {e}")
        _log.error(traceback.format_exc())
    finally:
        _log.info("程序已退出")