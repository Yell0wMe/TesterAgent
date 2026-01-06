#!/bin/bash

# TesterAgent 服务管理脚本

BACKEND_PORT=8000
FRONTEND_PORT=3000
LOG_DIR="./logs"

# 创建日志目录
mkdir -p $LOG_DIR

start() {
    echo "🚀 正在启动服务..."

    # 启动后端
    echo "  -> 启动后端 (Python)..."
    if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "     ⚠️ 后端端口 $BACKEND_PORT 已被占用，跳过。"
    else
        nohup .venv/bin/python -m src.server.app > $LOG_DIR/backend.log 2>&1 &
        echo "     ✅ 后端已在后台启动 (日志: $LOG_DIR/backend.log)"
    fi

    # 启动前端
    echo "  -> 启动前端 (Next.js)..."
    if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "     ⚠️ 前端端口 $FRONTEND_PORT 已被占用，跳过。"
    else
        (cd web && nohup npm run dev > ../$LOG_DIR/frontend.log 2>&1 &)
        echo "     ✅ 前端已在后台启动 (日志: $LOG_DIR/frontend.log)"
    fi

    echo "✨ 启动完成！访问: http://localhost:3000"
}

stop() {
    echo "🛑 正在停止服务..."

    # 停止后端
    B_PID=$(lsof -ti :$BACKEND_PORT)
    if [ ! -z "$B_PID" ]; then
        echo "  -> 停止后端 (PID: $B_PID)..."
        kill -9 $B_PID
    else
        echo "  -> 后端未运行。"
    fi

    # 停止前端
    F_PID=$(lsof -ti :$FRONTEND_PORT)
    if [ ! -z "$F_PID" ]; then
        echo "  -> 停止前端 (PID: $F_PID)..."
        kill -9 $F_PID
    else
        echo "  -> 前端未运行。"
    fi
    
    # 清理 Next.js 僵尸进程
    pkill -f "next-dev" >/dev/null 2>&1

    echo "✅ 服务已停止。"
}

status() {
    echo "📊 服务状态:"
    
    if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "  🟢 后端 (Port $BACKEND_PORT): 运行中"
    else
        echo "  🔴 后端 (Port $BACKEND_PORT): 已停止"
    fi

    if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "  🟢 前端 (Port $FRONTEND_PORT): 运行中"
    else
        echo "  🔴 前端 (Port $FRONTEND_PORT): 已停止"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
