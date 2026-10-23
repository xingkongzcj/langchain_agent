"""问答会话历史数据模型（L1 会话短期记忆）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessage(Base):
    """会话消息表。

    按 (course_id, session_id) 归组，问答时取最近若干轮拼进 Prompt，
    实现「它 / 这个 / 刚才那个」这类指代能接得上的多轮对话。
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        # 按会话取最近 N 条是唯一访问模式，联合索引覆盖
        Index("idx_chat_session", "course_id", "session_id", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courses.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # user / assistant
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
