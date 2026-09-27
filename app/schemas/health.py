"""健康检查 Schema。"""

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """健康检查数据。"""

    mysql: str = Field(description="MySQL 连通状态：ok / error")
    chroma: str = Field(description="Chroma 连通状态：ok / error")
