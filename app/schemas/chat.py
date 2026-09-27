"""问答 Schema。"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """问答请求。"""

    question: str = Field(min_length=1, description="问题")
    session_id: str | None = Field(default=None, description="会话 ID")


class Source(BaseModel):
    """引用来源。"""

    filename: str
    text: str


class ChatResponse(BaseModel):
    """问答响应。"""

    answer: str
    sources: list[Source] = Field(default_factory=list)
