"""
自动生成剩余模块的脚本
运行此脚本完成所有模块的实现
"""

import os 
from pathlib import Path 


PROJECT_ROOT =Path (__file__ ).parent .parent 

print ("🚀 开始生成所有模块...")
print (f"📂 项目根目录: {PROJECT_ROOT }")
print ()


print ("1️⃣ 生成 Command 模块...")


(PROJECT_ROOT /"src/feishu_bot/command/parser.py").write_text ('''"""
命令解析器
"""

from typing import Optional, Tuple


class CommandParser:
    """命令解析器"""
    
    @staticmethod
    def parse_remote_command(message: str) -> Optional[Tuple[str, str]]:
        """
        解析远程命令格式: <令牌>: <命令>
        返回: (token, command) 或 None
        """
        if ':' not in message:
            return None
        
        parts = message.split(':', 1)
        if len(parts) != 2:
            return None
        
        token = parts[0].strip()
        command = parts[1].strip()
        
        if not token or not command:
            return None
        
        return (token, command)
''',encoding ='utf-8')


(PROJECT_ROOT /"src/feishu_bot/command/validator.py").write_text ('''"""
命令验证器
"""

import logging

logger = logging.getLogger(__name__)


class CommandValidator:
    """命令验证器"""
    
    # 危险命令黑名单
    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
        "fork bomb",
        ":(){ :|:& };:"
    ]
    
    def validate_command(self, command: str) -> bool:
        """验证命令安全性"""
        if not command or not command.strip():
            return False
        
        command_lower = command.lower()
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command_lower:
                logger.warning(f"Blocked dangerous command: {command}")
                return False
        
        return True
    
    def validate_user(self, user_id: str) -> bool:
        """验证用户权限 (需要集成 security 模块)"""
        # TODO: 与 security 模块集成
        return True
''',encoding ='utf-8')


(PROJECT_ROOT /"src/feishu_bot/command/executor.py").write_text ('''"""
命令执行器
"""

import subprocess
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """命令执行结果"""
    token: str
    command: str
    success: bool
    method: str  # tmux, fallback, failed
    output: str = ""
    error: str = ""
    exec_time_ms: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TmuxCommandExecutor:
    """Tmux 命令执行器"""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
        from .parser import CommandParser
        from .validator import CommandValidator
        self.parser = CommandParser()
        self.validator = CommandValidator()
    
    def execute_command(self, token: str, command: str, user_id: str) -> CommandResult:
        """执行命令"""
        start_time = datetime.now()
        
        # 验证会话
        session = self.session_manager.validate_session(token)
        if session is None:
            return CommandResult(
                token=token,
                command=command,
                success=False,
                method="failed",
                error="Session validation failed",
                exec_time_ms=self._calc_exec_time(start_time)
            )
        
        # 验证命令
        if not self.validator.validate_command(command):
            return CommandResult(
                token=token,
                command=command,
                success=False,
                method="failed",
                error="Command validation failed",
                exec_time_ms=self._calc_exec_time(start_time)
            )
        
        # 执行 tmux 命令
        result = self._execute_in_tmux(session.tmux_session, command)
        result.token = token
        result.command = command
        result.exec_time_ms = self._calc_exec_time(start_time)
        
        # 更新会话活跃时间
        self.session_manager.update_session(token)
        
        logger.info(f"Command executed: token={token}, success={result.success}")
        return result
    
    def _execute_in_tmux(self, session_name: str, command: str) -> CommandResult:
        """在 tmux 会话中执行命令"""
        if not self._tmux_session_exists(session_name):
            return CommandResult(
                token="",
                command=command,
                success=False,
                method="failed",
                error=f"Tmux session '{session_name}' does not exist"
            )
        
        try:
            result = subprocess.run(
                ["tmux", "send-keys", "-t", session_name, command, "Enter"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return CommandResult(
                    token="",
                    command=command,
                    success=True,
                    method="tmux",
                    output="Command sent to tmux session successfully"
                )
            else:
                return self._fallback_execution(session_name, command)
        except Exception as e:
            return CommandResult(
                token="",
                command=command,
                success=False,
                method="failed",
                error=str(e)
            )
    
    def _fallback_execution(self, session_name: str, command: str) -> CommandResult:
        """回退执行方法"""
        try:
            result = subprocess.run(
                ["tmux", "send", "-t", session_name, command, "C-m"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return CommandResult(
                    token="",
                    command=command,
                    success=True,
                    method="fallback",
                    output="Command sent using alternative method"
                )
        except Exception:
            pass
        
        return CommandResult(
            token="",
            command=command,
            success=False,
            method="failed",
            error="All execution methods failed"
        )
    
    def _tmux_session_exists(self, session_name: str) -> bool:
        """检查 tmux 会话是否存在"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _calc_exec_time(self, start_time: datetime) -> int:
        """计算执行时间(毫秒)"""
        delta = datetime.now() - start_time
        return int(delta.total_seconds() * 1000)
''',encoding ='utf-8')


(PROJECT_ROOT /"src/feishu_bot/command/__init__.py").write_text ('''"""
Command 执行模块
"""

from .parser import CommandParser
from .validator import CommandValidator
from .executor import TmuxCommandExecutor, CommandResult

__all__ = [
    'CommandParser',
    'CommandValidator',
    'TmuxCommandExecutor',
    'CommandResult',
]
''',encoding ='utf-8')

print ("✅ Command 模块生成完成")


print ("2️⃣ 生成 Config 模块...")

(PROJECT_ROOT /"src/feishu_bot/config/config.py").write_text ('''"""
配置管理
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str
    app_secret: str


@dataclass
class WebhookConfig:
    """Webhook配置"""
    port: int = 8080
    host: str = "0.0.0.0"


@dataclass
class SessionConf:
    """Session配置"""
    storage_file: str = "data/sessions.json"
    token_length: int = 8
    expiration_hours: int = 24
    cleanup_interval_minutes: int = 60


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "data/logs/app.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class CardsConfig:
    """卡片配置"""
    task_completed_card_id: str = ""
    task_waiting_card_id: str = ""
    command_result_card_id: str = ""
    session_list_card_id: str = ""


@dataclass
class SecurityConfig:
    """安全配置"""
    whitelist_file: str = "configs/security/whitelist.yaml"
    max_command_length: int = 1000
    dangerous_commands: list = None


class Config:
    """应用配置"""
    
    def __init__(self):
        self.feishu: Optional[FeishuConfig] = None
        self.webhook: WebhookConfig = WebhookConfig()
        self.session: SessionConf = SessionConf()
        self.logging: LoggingConfig = LoggingConfig()
        self.cards: CardsConfig = CardsConfig()
        self.security: SecurityConfig = SecurityConfig()
    
    @classmethod
    def load_from_file(cls, config_path: str = "configs/config.yaml") -> 'Config':
        """从文件加载配置"""
        config = cls()
        
        # 加载YAML文件
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # 解析配置
            if 'feishu' in data:
                config.feishu = FeishuConfig(
                    app_id=cls._resolve_env(data['feishu'].get('app_id', '')),
                    app_secret=cls._resolve_env(data['feishu'].get('app_secret', ''))
                )
            
            if 'webhook' in data:
                config.webhook = WebhookConfig(**data['webhook'])
            
            if 'session' in data:
                config.session = SessionConf(**data['session'])
            
            if 'logging' in data:
                config.logging = LoggingConfig(**data['logging'])
            
            if 'cards' in data:
                config.cards = CardsConfig(**data['cards'])
            
            if 'security' in data:
                config.security = SecurityConfig(**data['security'])
        
        # 从环境变量覆盖
        config._load_from_env()
        
        return config
    
    def _load_from_env(self):
        """从环境变量加载"""
        # 飞书配置
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')
        if app_id and app_secret:
            self.feishu = FeishuConfig(app_id=app_id, app_secret=app_secret)
        
        # Webhook配置
        if os.getenv('WEBHOOK_PORT'):
            self.webhook.port = int(os.getenv('WEBHOOK_PORT'))
        
        # Session配置
        if os.getenv('SESSION_STORAGE_FILE'):
            self.session.storage_file = os.getenv('SESSION_STORAGE_FILE')
        
        # 日志配置
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL')
    
    @staticmethod
    def _resolve_env(value: str) -> str:
        """解析环境变量占位符"""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.load_from_file()
    return _config_instance
''',encoding ='utf-8')

(PROJECT_ROOT /"src/feishu_bot/config/__init__.py").write_text ('''"""
配置管理模块
"""

from .config import Config, get_config

__all__ = ['Config', 'get_config']
''',encoding ='utf-8')

print ("✅ Config 模块生成完成")

print ()
print ("="*50 )
print ("✅ 所有核心模块生成完成!")
print ()
print ("下一步:")
print ("1. 实现飞书 Bot 客户端和通知模块")
print ("2. 创建服务入口文件")
print ("3. 测试完整功能")
print ()
print ("运行测试: venv\\Scripts\\python.exe -m pytest tests/")
