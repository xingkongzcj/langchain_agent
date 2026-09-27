"""FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.response import ApiResponse
from app.db.chroma import check_chroma
from app.db.mysql import check_mysql, init_db
from app.schemas.health import HealthData

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时初始化数据库建表。"""
    init_db()
    yield


# 创建 FastAPI 实例
app = FastAPI(
    title="智学助手",
    description="基于 LangChain 的课程知识库问答与出题智能体",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册全局异常处理器
register_exception_handlers(app)

# 配置 CORS 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动信息（不打印密钥）
logger.info("LLM 模型: %s", settings.llm_model)
logger.info("Embedding 模型: %s", settings.embedding_model)


@app.get("/")
def root() -> dict:
    """根路径。"""
    return {
        "message": "欢迎使用智学助手",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/api/health")
def health_check() -> ApiResponse[HealthData]:
    """健康检查：验证 MySQL 与 Chroma 连通性。"""
    return ApiResponse.success(
        data=HealthData(
            mysql="ok" if check_mysql() else "error",
            chroma="ok" if check_chroma() else "error",
        )
    )
