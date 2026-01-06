#!/bin/bash

# TesterAgent 一键部署脚本 (Linux)
set -e

echo "🚀 开始部署 TesterAgent..."

# 1. 检查操作系统与包管理器
if [ -f /etc/debian_version ]; then
    PKG_MANAGER="apt-get"
    UPDATE_CMD="sudo apt-get update"
    INSTALL_CMD="sudo apt-get install -y"
    deps=("python3" "python3-venv" "python3-pip" "nodejs" "npm" "adb" "git" "libgbm-dev")
elif [ -f /etc/redhat-release ]; then
    PKG_MANAGER="yum"
    UPDATE_CMD="sudo yum check-update"
    INSTALL_CMD="sudo yum install -y"
    deps=("python3" "nodejs" "npm" "android-tools" "git")
else
    echo "❌ 不支持的操作系统。请手动安装依赖。"
    exit 1
fi

# 2. 安装系统依赖
echo "📦 检查并安装系统依赖..."
$UPDATE_CMD || true
for dep in "${deps[@]}"; do
    if ! command -v $dep &> /dev/null && [ "$dep" != "python3-venv" ] && [ "$dep" != "python3-pip" ] && [ "$dep" != "libgbm-dev" ]; then
        echo "  -> 安装 $dep..."
        $INSTALL_CMD $dep
    fi
done

# 特殊处理 python3-venv (Ubuntu/Debian)
if [ "$PKG_MANAGER" == "apt-get" ]; then
    $INSTALL_CMD python3-venv python3-pip libgbm-dev
fi

# 3. 后端环境配置
echo "🐍 配置 Python 后端环境..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  ✅ 已创建虚拟环境。"
fi

source .venv/bin/activate
pip install --upgrade pip
echo "  -> 安装依赖包 (可能需要一些时间)..."
pip install -e ".[dev,zhipu]"

echo "  -> 安装 Playwright 浏览器及其系统依赖..."
playwright install chromium
if [ "$PKG_MANAGER" == "apt-get" ]; then
    python3 -m playwright install-deps chromium
fi

# 4. 前端环境配置
echo "🌐 配置 Node.js 前端环境..."
if [ -d "web" ]; then
    cd web
    echo "  -> 安装 npm 包..."
    npm install
    # echo "  -> 构建前端任务 (可选)..."
    # npm run build
    cd ..
else
    echo "⚠️ 未找到 web 目录，跳过前端配置。"
fi

# 5. 配置文件检查
echo "⚙️ 检查配置文件..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  ✅ 已从 .env.example 创建 .env 文件。"
        echo "  ❗ 请务必编辑 .env 文件并填入 ZHIPU_API_KEY。"
    else
        touch .env
        echo "  ⚠️ 未找到 .env.example，已创建空的 .env 文件。"
    fi
fi

# 6. 设置权限
chmod +x manage.sh

echo ""
echo "🎉 部署完成！"
echo "-------------------------------------------------------"
echo "下一步操作："
echo "1. 编辑 .env 文件，配置您的 API Key。"
echo "2. 使用 ./manage.sh start 启动服务。"
echo "3. 访问 http://localhost:3000 开始使用。"
echo "-------------------------------------------------------"
