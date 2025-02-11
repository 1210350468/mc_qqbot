import os
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import asyncio
import threading
from contextlib import asynccontextmanager
from demo_group_reply_text import BotRunner, get_public_ip
from botpy import logging

_log = logging.get_logger()

# 全局变量存储机器人实例
bot_runner = None
bot_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    处理应用的生命周期事件
    """
    # 启动事件
    global bot_thread
    try:
        # 在新线程中启动机器人
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        _log.info("机器人线程已启动")
    except Exception as e:
        _log.error(f"机器人启动失败: {e}")
        raise
    
    yield  # FastAPI 运行中
    
    # 关闭事件
    global bot_runner
    if bot_runner:
        bot_runner.stop()
        _log.info("机器人已停止")

# 创建 FastAPI 应用
app = FastAPI(lifespan=lifespan)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_bot():
    """在新线程中运行机器人"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 获取并打印公网IP
    public_ip = loop.run_until_complete(get_public_ip())
    _log.info(f"本机公网IP: {public_ip}")
    
    # 创建并启动机器人
    global bot_runner
    bot_runner = BotRunner(max_retries=None, retry_delay=30)
    loop.run_until_complete(bot_runner.start_bot())

@app.get("/")
async def root():
    """根路径处理"""
    return {"status": "ok", "message": "QQ机器人服务正在运行"}

@app.get("/status")
async def get_status():
    """健康检查接口"""
    global bot_runner
    is_running = bot_runner is not None and bot_runner.running
    return {
        "status": "running" if is_running else "stopped",
        "retry_count": bot_runner.retry_count if bot_runner else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 