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
