"""MySQL 数据库连接与会话管理。"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

# 构造 MySQL 连接串（使用 pymysql 驱动）
DATABASE_URL = (
    f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
    f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    "?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有数据库表（启动时调用，失败不阻断启动）。"""
    import app.models  # noqa: F401  确保模型已注册到 Base.metadata

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("MySQL 表结构初始化完成")
    except Exception as exc:
        logger.error("MySQL 建表失败: %s", exc)


def check_mysql() -> bool:
    """检查 MySQL 是否连通。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
