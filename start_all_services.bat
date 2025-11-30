@echo off
REM 启动所有服务

echo ====================================
echo  飞书 Claude Code 远程控制机器人
echo ====================================
echo.

echo [1/2] 启动 Webhook 服务 (端口 8080)...
start "Webhook Service" cmd /k "venv\Scripts\python.exe services\webhook_service.py"
timeout /t 2 /nobreak >nul

echo [2/2] 启动 Bot 服务 (端口 8081)...
start "Bot Service" cmd /k "venv\Scripts\python.exe services\bot_service.py"
timeout /t 2 /nobreak >nul

echo.
echo ✅ 所有服务已启动
echo.
echo 📋 服务地址:
echo   - Webhook 服务: http://localhost:8080
echo   - Bot 服务: http://localhost:8081
echo   - Webhook API 文档: http://localhost:8080/docs
echo   - Bot API 文档: http://localhost:8081/docs
echo.
echo 📝 使用说明:
echo   1. 在飞书开放平台配置事件订阅URL: http://your-server:8081/webhook/event
echo   2. Claude Code webhook通知URL: http://your-server:8080/webhook/notification
echo   3. 在飞书发送消息测试: /help
echo.
echo 按任意键退出...
pause >nul
