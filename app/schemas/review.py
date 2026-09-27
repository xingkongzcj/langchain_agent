"""复习计划 Schema。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewPlanCreate(BaseModel):
    """创建复习计划请求。"""

    name: str | None = Field(default=None, description="计划名称")


class ReviewItemOut(BaseModel):
    """复习条目响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    question_id: int | None = None
    knowledge_point: str | None = None
    review_date: date
    completed: bool
    created_at: datetime


class ReviewPlanOut(BaseModel):
    """复习计划响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    name: str
    description: str | None = None
    status: str
    created_at: datetime
    items: list[ReviewItemOut] = Field(default_factory=list)
