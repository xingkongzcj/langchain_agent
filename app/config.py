"""应用配置模块：使用 pydantic-settings 从 .env 文件读取配置。"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。

    从项目根目录的 .env 文件读取环境变量，字段名自动映射为对应的大写环境变量名
    （如 `mysql_host` -> `MYSQL_HOST`）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============ 硅基流动（SiliconFlow）OpenAI 兼容接口 ============
    siliconflow_api_key: str = Field(default="", description="硅基流动 API Key")
    siliconflow_base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="硅基流动 Base URL",
    )
    llm_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct", description="大语言模型")
    embedding_model: str = Field(default="BAAI/bge-m3", description="Embedding 模型")
    top_k: int = Field(default=4, description="检索召回数量")

    # ============ MySQL 业务数据库 ============
    mysql_host: str = Field(default="localhost", description="MySQL 主机")
    mysql_port: int = Field(default=3307, description="MySQL 端口")
    mysql_user: str = Field(default="root", description="MySQL 用户名")
    mysql_password: str = Field(default="", description="MySQL 密码")
    mysql_database: str = Field(default="study_mate", description="MySQL 数据库名")

    # ============ Chroma 向量数据库（本地持久化） ============
    chroma_persist_dir: str = Field(default="./chroma_db", description="Chroma 本地持久化目录")


# 模块级配置单例，导入时即完成 .env 读取
settings = Settings()
