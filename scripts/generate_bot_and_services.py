"""
生成Bot客户端和服务入口的脚本
"""

import os 
from pathlib import Path 

PROJECT_ROOT =Path (__file__ ).parent .parent 

print ("🚀 生成 Bot 客户端和服务...")
print ()


print ("1️⃣ 生成 Bot 客户端...")

(PROJECT_ROOT /"src/feishu_bot/bot/client.py").write_text ('''"""
飞书客户端封装
"""

import logging
from lark_oapi import Client
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse
)

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = Client.builder() \\
            .app_id(app_id) \\
            .app_secret(app_secret) \\
            .build()
        logger.info(f"Feishu client initialized: app_id={app_id}")
    
    def send_text_message(self, open_id: str, text: str) -> bool:
        """发送文本消息"""
        try:
            request = CreateMessageRequest.builder() \\
                .receive_id_type("open_id") \\
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("text")
                    .content(f'{{"text":"{text}"}}')
                    .build()
                ).build()
            
            response: CreateMessageResponse = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"Failed to send message: {response.code} - {response.msg}")
                return False
            
            logger.info(f"Message sent successfully to {open_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_card(self, open_id: str, card_content: str) -> bool:
        """发送卡片消息"""
        try:
            request = CreateMessageRequest.builder() \\
                .receive_id_type("open_id") \\
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(open_id)
                    .msg_type("interactive")
                    .content(card_content)
                    .build()
                ).build()
            
            response = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"Failed to send card: {response.code} - {response.msg}")
                return False
            
            logger.info(f"Card sent successfully to {open_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending card: {e}")
            return False
''',encoding ='utf-8')

(PROJECT_ROOT /"src/feishu_bot/bot/__init__.py").write_text ('''"""
Bot 模块
"""

from .client import FeishuClient

__all__ = ['FeishuClient']
''',encoding ='utf-8')

print ("✅ Bot 客户端生成完成")


print ("2️⃣ 生成 Webhook 服务...")

(PROJECT_ROOT /"services/webhook_service.py").write_text ('''"""
Webhook 服务入口
"""

import os
import sys
import logging
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from feishu_bot.session import SessionManager, SessionConfig
from feishu_bot.config import get_config
from feishu_bot.security import UserMappingService
from feishu_bot.bot import FeishuClient
from feishu_bot.notification import (
    WebhookRequest,
    WebhookResponse,
    NotificationSender,
    WebhookHandler
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 加载配置
config = get_config()

# 初始化组件
session_manager = SessionManager(
    config.session.storage_file,
    SessionConfig(
        token_length=config.session.token_length,
        expiration_hours=config.session.expiration_hours,
        cleanup_interval_minutes=config.session.cleanup_interval_minutes
    )
)

# 初始化用户映射服务
try:
    user_mapping_service = UserMappingService(config.security.whitelist_file)
except Exception as e:
    logger.warning(f"Failed to load user mapping service: {e}")
    user_mapping_service = None

# 初始化飞书客户端
if not config.feishu:
    logger.error("Feishu configuration not found!")
    sys.exit(1)

feishu_client = FeishuClient(config.feishu.app_id, config.feishu.app_secret)

# 初始化通知发送器
notification_sender = NotificationSender(feishu_client)

# 初始化 webhook 处理器
webhook_handler = WebhookHandler(
    session_manager,
    notification_sender,
    user_mapping_service
)

# 创建 FastAPI 应用
app = FastAPI(
    title="Feishu Bot Webhook Service",
    description="Claude Code 远程控制机器人 Webhook 服务",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "webhook",
        "feishu_app_id": config.feishu.app_id
    }


@app.post("/webhook/notification", response_model=WebhookResponse)
async def receive_notification(req: WebhookRequest):
    """接收 Claude Code 通知"""
    try:
        return webhook_handler.handle_notification(req)
    except Exception as e:
        logger.error(f"Error handling notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook/session/{token}")
async def get_session(token: str):
    """获取会话信息"""
    session = webhook_handler.get_session_info(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "token": session.token,
        "user_id": session.user_id,
        "open_id": session.open_id,
        "tmux_session": session.tmux_session,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat() if session.expires_at else None
    }


@app.get("/webhook/stats")
async def get_stats():
    """获取统计信息"""
    return webhook_handler.get_stats()


@app.post("/webhook/cleanup")
async def cleanup_sessions():
    """手动清理过期会话"""
    cleaned = webhook_handler.cleanup_expired_sessions()
    return {"cleaned_sessions": cleaned}


if __name__ == "__main__":
    port = config.webhook.port
    logger.info(f"Starting webhook service on port {port}")
    logger.info(f"API docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host=config.webhook.host,
        port=port,
        log_level="info"
    )
''',encoding ='utf-8')

print ("✅ Webhook 服务生成完成")


print ("3️⃣ 生成 Bot 服务 (简化版)...")

(PROJECT_ROOT /"services/bot_service.py").write_text ('''"""
Bot 服务入口 (简化版 - 仅处理消息)
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from feishu_bot.session import SessionManager, SessionConfig
from feishu_bot.config import get_config
from feishu_bot.bot import FeishuClient
from feishu_bot.command import CommandParser, TmuxCommandExecutor
from feishu_bot.notification import NotificationSender

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    # 加载配置
    config = get_config()
    
    # 初始化组件
    session_manager = SessionManager(
        config.session.storage_file,
        SessionConfig(
            token_length=config.session.token_length,
            expiration_hours=config.session.expiration_hours,
            cleanup_interval_minutes=config.session.cleanup_interval_minutes
        )
    )
    
    if not config.feishu:
        logger.error("Feishu configuration not found!")
        sys.exit(1)
    
    feishu_client = FeishuClient(config.feishu.app_id, config.feishu.app_secret)
    notification_sender = NotificationSender(feishu_client)
    command_executor = TmuxCommandExecutor(session_manager)
    parser = CommandParser()
    
    logger.info("Bot service initialized")
    logger.info("Note: WebSocket integration requires additional implementation")
    logger.info("For now, use Webhook service to receive notifications")
    
    # TODO: 实现 WebSocket 长连接
    # from lark_oapi.ws import Client as WSClient
    # ws_client = WSClient(config.feishu.app_id, config.feishu.app_secret)
    # ws_client.start()


if __name__ == "__main__":
    main()
''',encoding ='utf-8')

print ("✅ Bot 服务生成完成")

print ()
print ("="*50 )
print ("✅ 所有模块和服务生成完成!")
print ()
print ("下一步:")
print ("1. 测试模块导入: venv\\Scripts\\python.exe -c \"from src.feishu_bot import *\"")
print ("2. 启动 Webhook 服务: venv\\Scripts\\python.exe services/webhook_service.py")
print ("3. 测试 webhook 接收")
print ()
