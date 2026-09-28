"""错题本路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.mistake import (
    MistakeListItem,
    MistakeOut,
    MistakeUpdate,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services import mistake_service

router = APIRouter(prefix="/api", tags=["错题本"])


@router.post("/questions/{question_id}/submit")
def submit_answer(
    question_id: int,
    data: SubmitAnswerRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[SubmitAnswerResponse]:
    """提交答案并判题。"""
    result = mistake_service.submit_answer(db, question_id, data.user_answer)
    return ApiResponse.success(data=SubmitAnswerResponse(**result))


@router.get("/courses/{course_id}/mistakes")
def list_mistakes(
    course_id: int,
    status: str | None = Query(default=None, description="错题状态"),
    db: Session = Depends(get_db),
) -> ApiResponse[list[MistakeListItem]]:
    """获取错题本列表。"""
    items = mistake_service.list_mistakes(db, course_id, status)
    return ApiResponse.success(data=[MistakeListItem(**item) for item in items])


@router.patch("/mistakes/{mistake_id}")
def update_mistake(
    mistake_id: int,
    data: MistakeUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[MistakeOut]:
    """标记掌握/未掌握。"""
    mistake = mistake_service.update_mistake(db, mistake_id, data.status)
    return ApiResponse.success(data=MistakeOut.model_validate(mistake))


@router.delete("/mistakes/{mistake_id}")
def delete_mistake(
    mistake_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """移除错题记录。"""
    mistake_service.delete_mistake(db, mistake_id)
    return ApiResponse.success(message="错题移除成功")
