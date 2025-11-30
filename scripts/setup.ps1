# 飞书机器人 Python 版本 - 安装脚本 (Windows)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "飞书 Claude Code 机器人 - 安装向导" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 版本
Write-Host "检查 Python 版本..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到 Python! 请先安装 Python 3.10 或更高版本" -ForegroundColor Red
    exit 1
}
Write-Host "找到 Python: $pythonVersion" -ForegroundColor Green

# 创建虚拟环境
Write-Host ""
Write-Host "创建虚拟环境..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "虚拟环境已存在，跳过创建" -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 创建虚拟环境失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "虚拟环境创建成功" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host ""
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# 升级 pip
Write-Host ""
Write-Host "升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# 安装依赖
Write-Host ""
Write-Host "安装项目依赖..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 安装依赖失败" -ForegroundColor Red
    exit 1
}
Write-Host "依赖安装成功" -ForegroundColor Green

# 复制环境变量文件
Write-Host ""
Write-Host "配置环境变量..." -ForegroundColor Yellow
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "已创建 .env 文件，请编辑填入你的飞书应用信息" -ForegroundColor Green
    Write-Host "  FEISHU_APP_ID=your_app_id" -ForegroundColor Cyan
    Write-Host "  FEISHU_APP_SECRET=your_app_secret" -ForegroundColor Cyan
} else {
    Write-Host ".env 文件已存在" -ForegroundColor Yellow
}

# 创建数据目录
Write-Host ""
Write-Host "创建数据目录..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data\logs" | Out-Null
Write-Host "数据目录创建完成" -ForegroundColor Green

# 完成
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "安装完成!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 编辑 .env 文件，填入飞书应用配置" -ForegroundColor White
Write-Host "2. 编辑 configs/security/whitelist.yaml，配置用户权限" -ForegroundColor White
Write-Host "3. 运行 webhook 服务: python services/webhook_service.py" -ForegroundColor White
Write-Host "4. 运行 bot 服务: python services/bot_service.py" -ForegroundColor White
Write-Host ""
Write-Host "查看详细文档: README.md" -ForegroundColor Cyan
