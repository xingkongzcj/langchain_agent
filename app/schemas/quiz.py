"""出题与题目 Schema。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class QuizGenerateRequest(BaseModel):
    """生成题目请求。"""

    topic: str | None = Field(default=None, description="出题主题")
    question_type: Literal["single", "multiple", "judge", "short", "mixed"] = Field(
        default="single", description="题型"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium", description="难度")
    count: int = Field(default=5, ge=1, le=50, description="题目数量")


class QuestionOut(BaseModel):
    """题目响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    course_id: int
    type: str
    question: str
    options: Any | None = None
    answer: str | None = None
    explanation: str | None = None
    created_at: datetime


class QuizBatchOut(BaseModel):
    """出题批次响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    topic: str | None = None
    question_type: str
    difficulty: str
    count: int
    created_at: datetime
    questions: list[QuestionOut] = Field(default_factory=list)
