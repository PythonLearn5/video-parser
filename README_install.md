# Video Parser  安装配置

### 安装依赖

```bash
conda create -n videoparser python=3.10
conda activate videoparser

pip install -r requirements.txt


# 启动后端 API 服务（端口 5001）：

python api.py
# 启动 Gradio 前端（端口 7860）：

python app.py
```

### docker本地安装

docker login
docker pull python:3.11-slim
docker-compose up -d --build
不用缓存
docker compose build --no-cache
docker compose up -d
查看日志
docker-compose logs -f

停止服务
docker-compose down

