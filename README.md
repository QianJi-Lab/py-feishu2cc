# 🤖 飞书 Claude Code 远程控制机器人
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()

**状态**: ✅ 核心功能已完成，可投入使用，稍微有一个 bug 就是会重复发送指令，正在施工🚧ing

通过飞书机器人实时接收 Claude Code 任务通知，并支持远程发送命令到 Claude Code 会话。

目前基于 Windows，后期考虑迭代

## ✨ 主要功能

- ✅ 📬 **实时接收通知** - Claude Code 任务完成/等待输入通知
- ✅ 📝 **任务输出显示** - 自动捕获并显示 Claude 的回复内容
- ✅ ⌨️ **远程发送命令** - 通过飞书消息控制 tmux 会话

## 🚀 快速开始

### 1. 启动服务

```bash
# 一键启动所有服务
start_all_services.bat
```

或手动启动:

```bash
# 终端1 - Webhook 服务 (端口 8080)
venv\Scripts\python.exe services\webhook_service.py

# 终端2 - Bot 服务 (端口 8081)
venv\Scripts\python.exe services\bot_service.py
```

### 2. 配置飞书

1. **事件订阅 URL**:
   ```
   http://your-server:8081/webhook/event
   ```

2. **Claude Code Webhook**:
   ```
   http://your-server:8080/webhook/notification
   ```

## 技术栈

- **Web 框架**: FastAPI
- **飞书 SDK**: lark-oapi
- **数据验证**: Pydantic
- **任务调度**: APScheduler
- **异步支持**: asyncio

---

## 开发状态

**完成度: 50%** (核心功能)

### 已实现模块
- ✅ Command 命令执行 (解析、验证)
- ✅ Config 配置管理 (YAML + 环境变量)
- ✅ Notification 通知系统 (飞书消息发送)
- ✅ Bot Client 飞书客户端 (SDK封装)
- ✅ Webhook Service (HTTP服务)
- ✅ Bot Service (消息处理)

## 许可证

MIT License
