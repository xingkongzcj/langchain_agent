"""课程 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    """创建课程请求。"""

    name: str = Field(min_length=1, max_length=255, description="课程名称")
    description: str | None = Field(default=None, description="课程描述")


class CourseOut(BaseModel):
    """课程响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime
