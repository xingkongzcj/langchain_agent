"""错题本 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MistakeUpdate(BaseModel):
    """更新错题状态请求。"""

    status: Literal["unmastered", "mastered"] = Field(..., description="掌握状态")


class MistakeOut(BaseModel):
    """错题响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    question_id: int
    user_answer: str
    status: str
    review_count: int
    created_at: datetime


class SubmitAnswerRequest(BaseModel):
    """提交答案请求。"""

    user_answer: str = Field(min_length=1, description="用户答案")


class SubmitAnswerResponse(BaseModel):
    """提交答案判题结果。"""

    correct: bool
    correct_answer: str | None = None
    explanation: str | None = None
    score: int | None = None
    reason: str | None = None
    mistake_id: int | None = None
    llm_raw: str | None = None


class MistakeListItem(BaseModel):
    """错题本列表项（含题干与正确答案）。"""

    id: int
    question_id: int
    question: str
    user_answer: str
    correct_answer: str | None = None
    explanation: str | None = None
    status: str
    review_count: int
    created_at: datetime
