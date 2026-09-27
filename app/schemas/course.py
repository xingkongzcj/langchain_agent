"""课程 Schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentOut


class CourseCreate(BaseModel):
    """创建课程请求。"""

    name: str = Field(min_length=1, max_length=255, description="课程名称")
    description: str | None = Field(default=None, description="课程描述")


class CourseOut(BaseModel):
    """课程基础响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime


class CourseListItem(CourseOut):
    """课程列表项（含文档数量）。"""

    doc_count: int = 0


class CourseDetailOut(CourseOut):
    """课程详情（含文档列表）。"""

    documents: list[DocumentOut] = Field(default_factory=list)
