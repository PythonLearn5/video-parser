#!/bin/sh
set -e

echo "=========================================="
echo "  Video Parser - Starting Services"
echo "=========================================="

# 创建必要的目录
mkdir -p static/videos static/images downloads cache logs

# 启动 FastAPI 后端 (后台运行)
echo "[1/2] Starting FastAPI backend on port 5001..."
python api.py &
API_PID=$!

# 等待 API 启动
sleep 3

# 检查 API 是否成功启动
if ! kill -0 $API_PID 2>/dev/null; then
    echo "Error: FastAPI backend failed to start"
    exit 1
fi

echo "[1/2] FastAPI backend started successfully (PID: $API_PID)"

# 启动 Gradio 前端 (前台运行)
echo "[2/2] Starting Gradio frontend on port 7860..."
python app.py

# 如果 Gradio 退出，也停止 API
kill $API_PID 2>/dev/null || true
