"""智能问答路由（含会话历史与清空）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services import memory_service, rag_service

router = APIRouter(prefix="/api/courses", tags=["智能问答"])


@router.post("/{course_id}/chat")
def chat(
    course_id: int,
    data: ChatRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[ChatResponse]:
    """RAG 智能问答（带多轮上下文）。"""
    result = rag_service.chat_with_knowledge(
        db=db,
        course_id=course_id,
        question=data.question,
        session_id=data.session_id,
    )
    return ApiResponse.success(data=result)


@router.get("/{course_id}/chat/history")
def chat_history(
    course_id: int,
    session_id: str = Query(..., max_length=64, description="会话 ID"),
    db: Session = Depends(get_db),
) -> ApiResponse[list[ChatMessageOut]]:
    """获取某个会话的历史消息（刷新页面后恢复对话）。"""
    messages = memory_service.list_session_messages(db, course_id, session_id)
    return ApiResponse.success(data=[ChatMessageOut(**item) for item in messages])


@router.delete("/{course_id}/chat/{session_id}")
def clear_chat(
    course_id: int,
    session_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """清空会话记录（隐私：用户可随时删除聊天内容）。"""
    deleted = memory_service.clear_session(db, course_id, session_id)
    return ApiResponse.success(message=f"已清空 {deleted} 条对话")
