"""问答 Schema。"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """问答请求。"""

    question: str = Field(min_length=1, description="问题")
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description="会话 ID（前端生成；为空则退化为单轮问答，不留历史）",
    )


class Source(BaseModel):
    """引用来源。"""

    filename: str
    text: str


class ChatResponse(BaseModel):
    """问答响应。"""

    answer: str
    sources: list[Source] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    """会话消息（前端回显用）。"""

    role: Literal["user", "assistant"] = Field(description="消息角色")
    content: str = Field(description="消息内容")
