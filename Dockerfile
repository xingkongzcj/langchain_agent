# syntax=docker/dockerfile:1
# 智学助手（StudyMate）生产镜像
# 构建：docker build -t studymate-app:1.0.0 .
# 基础镜像可用 --build-arg BASE_IMAGE=... 切换（国内拉不到 Docker Hub 时走镜像站）
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

# 国内服务器构建时走阿里云 PyPI 镜像；海外可覆盖为 https://pypi.org/simple
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# tzdata：复习计划按「本地日期」生成 7 天计划，容器默认 UTC 会错位 8 小时
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# 依赖单独成层，代码改动时可命中缓存
COPY requirements.txt .
RUN pip install -i "${PIP_INDEX_URL}" -r requirements.txt

# 应用代码与前端静态资源
COPY app ./app
COPY static ./static

# 非 root 运行；/data/chroma 为向量库持久化目录（由 compose 挂载卷）
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/chroma \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

# 健康检查（仅依赖标准库，避免镜像里再装 curl）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
