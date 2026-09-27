"""文档 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# 文档入库状态
DocumentStatus = Literal["processing", "completed", "failed"]


class DocumentOut(BaseModel):
    """文档响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    filename: str
    file_type: str | None = None
    file_size: int | None = None
    chunk_count: int
    status: DocumentStatus
    error: str | None = None
    created_at: datetime
