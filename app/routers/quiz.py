"""自动出题路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.quiz import QuestionOut, QuizBatchOut, QuizGenerateRequest
from app.services import quiz_service

router = APIRouter(prefix="/api/courses", tags=["自动出题"])


@router.post("/{course_id}/quizzes/generate")
def generate_quiz(
    course_id: int,
    data: QuizGenerateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[QuizBatchOut]:
    """基于课程知识库生成题目。"""
    batch = quiz_service.generate_quiz(
        db=db,
        course_id=course_id,
        topic=data.topic,
        question_type=data.question_type,
        difficulty=data.difficulty,
        count=data.count,
    )
    questions = quiz_service.list_questions(db, course_id, batch.id)
    result = QuizBatchOut(
        id=batch.id,
        course_id=batch.course_id,
        topic=batch.topic,
        question_type=batch.question_type,
        difficulty=batch.difficulty,
        count=batch.count,
        created_at=batch.created_at,
        questions=[QuestionOut.model_validate(q) for q in questions],
    )
    return ApiResponse.success(data=result, message="题目生成成功")


@router.get("/{course_id}/quizzes")
def list_quizzes(
    course_id: int,
    batch_id: int | None = Query(default=None, description="出题批次 ID"),
    db: Session = Depends(get_db),
) -> ApiResponse[list[QuestionOut]]:
    """获取课程下的题目列表（可按 batch_id 筛选）。"""
    questions = quiz_service.list_questions(db, course_id, batch_id)
    return ApiResponse.success(data=[QuestionOut.model_validate(q) for q in questions])
