"""智能问答路由。"""

from fastapi import APIRouter

from app.core.response import ApiResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import rag_service

router = APIRouter(prefix="/api/courses", tags=["智能问答"])


@router.post("/{course_id}/chat")
def chat(course_id: int, data: ChatRequest) -> ApiResponse[ChatResponse]:
    """RAG 智能问答。"""
    result = rag_service.chat_with_knowledge(
        course_id=course_id,
        question=data.question,
        session_id=data.session_id,
    )
    return ApiResponse.success(data=result)
