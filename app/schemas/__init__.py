"""Pydantic v2 请求/响应 Schema 模块。"""

from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.schemas.course import CourseCreate, CourseDetailOut, CourseListItem, CourseOut
from app.schemas.document import DocumentOut, DocumentStatus
from app.schemas.health import HealthData
from app.schemas.mistake import MistakeOut, MistakeUpdate
from app.schemas.quiz import QuestionOut, QuizBatchOut, QuizGenerateRequest
from app.schemas.review import ReviewItemOut, ReviewPlanCreate, ReviewPlanOut

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "CourseCreate",
    "CourseDetailOut",
    "CourseListItem",
    "CourseOut",
    "DocumentOut",
    "DocumentStatus",
    "HealthData",
    "MistakeOut",
    "MistakeUpdate",
    "QuestionOut",
    "QuizBatchOut",
    "QuizGenerateRequest",
    "ReviewItemOut",
    "ReviewPlanCreate",
    "ReviewPlanOut",
    "Source",
]
