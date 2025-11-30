#!/bin/bash
# 飞书机器人 Python 版本 - 安装脚本 (Linux/Mac)

echo "=================================="
echo "飞书 Claude Code 机器人 - 安装向导"
echo "=================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3! 请先安装 Python 3.10 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "找到 Python: $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "创建虚拟环境..."
if [ -d "venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误: 创建虚拟环境失败"
        exit 1
    fi
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "升级 pip..."
python -m pip install --upgrade pip

# 安装依赖
echo ""
echo "安装项目依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 安装依赖失败"
    exit 1
fi
echo "依赖安装成功"

# 复制环境变量文件
echo ""
echo "配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "已创建 .env 文件，请编辑填入你的飞书应用信息"
    echo "  FEISHU_APP_ID=your_app_id"
    echo "  FEISHU_APP_SECRET=your_app_secret"
else
    echo ".env 文件已存在"
fi

# 创建数据目录
echo ""
echo "创建数据目录..."
mkdir -p data/logs
echo "数据目录创建完成"

# 完成
echo ""
echo "=================================="
echo "安装完成!"
echo "=================================="
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件，填入飞书应用配置"
echo "2. 编辑 configs/security/whitelist.yaml，配置用户权限"
echo "3. 运行 webhook 服务: python services/webhook_service.py"
echo "4. 运行 bot 服务: python services/bot_service.py"
echo ""
echo "查看详细文档: README.md"
