FROM python:3.11-slim

# 设置维护者信息
LABEL maintainer="video-parser"
LABEL version="2.0.0"
LABEL description="Video Parser - 多平台视频解析下载系统 (FastAPI + Gradio + AI内容提取)"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Asia/Shanghai

# Qwen API 默认配置（可通过 .env 文件或 docker-compose 覆盖）
ENV QWEN_API_BASE_URL=https://api-inference.modelscope.cn/v1
ENV QWEN_MODEL_ID=Qwen/Qwen3-VL-8B-Instruct
ENV MAX_FRAMES=6

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用文件
COPY . .

# 创建必要的目录
RUN mkdir -p static/videos static/images downloads cache logs \
    && chmod -R 755 static downloads cache logs

# 暴露端口
# 5001: FastAPI 后端
# 7860: Gradio 前端
EXPOSE 5001 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 复制启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh

# 启动命令
ENTRYPOINT ["/docker-entrypoint.sh"]
