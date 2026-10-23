"""课程业务逻辑。"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.db.chroma import delete_collection
from app.models.chat import ChatMessage
from app.models.course import Course
from app.models.document import Document as DocumentModel
from app.models.mistake import Mistake
from app.models.quiz import Question, QuizBatch
from app.models.review import ReviewItem, ReviewPlan
from app.schemas.course import CourseCreate, CourseDetailOut, CourseListItem
from app.schemas.document import DocumentOut


def create_course(db: Session, data: CourseCreate) -> Course:
    """创建课程。"""
    course = Course(name=data.name, description=data.description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_courses(db: Session) -> list[CourseListItem]:
    """获取课程列表（含文档数量）。"""
    courses = db.query(Course).order_by(Course.id.desc()).all()

    # 统计每个课程的文档数量
    doc_counts = dict(
        db.query(DocumentModel.course_id, func.count(DocumentModel.id))
        .group_by(DocumentModel.course_id)
        .all()
    )

    return [
        CourseListItem(
            id=course.id,
            name=course.name,
            description=course.description,
            created_at=course.created_at,
            doc_count=doc_counts.get(course.id, 0),
        )
        for course in courses
    ]


def get_course(db: Session, course_id: int) -> CourseDetailOut:
    """获取课程详情（含文档列表）。"""
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=404, message="课程不存在")

    documents = (
        db.query(DocumentModel)
        .filter(DocumentModel.course_id == course_id)
        .order_by(DocumentModel.id.desc())
        .all()
    )

    return CourseDetailOut(
        id=course.id,
        name=course.name,
        description=course.description,
        created_at=course.created_at,
        documents=[DocumentOut.model_validate(d) for d in documents],
    )


def delete_course(db: Session, course_id: int) -> None:
    """删除课程，级联删除关联数据与 Chroma 向量。

    按外键依赖顺序删除：review_items -> review_plans -> mistakes
    -> questions -> quiz_batches -> documents -> courses。
    """
    course = db.get(Course, course_id)
    if not course:
        raise BusinessException(code=404, message="课程不存在")

    # 1. 清理 Chroma 向量 collection
    delete_collection(f"course_{course_id}")

    # 2. 级联删除关联数据（先删子表，再删父表）
    plan_ids = [
        pid
        for (pid,) in db.query(ReviewPlan.id)
        .filter(ReviewPlan.course_id == course_id)
        .all()
    ]
    if plan_ids:
        db.query(ReviewItem).filter(ReviewItem.plan_id.in_(plan_ids)).delete(
            synchronize_session=False
        )

    db.query(ReviewPlan).filter(ReviewPlan.course_id == course_id).delete(
        synchronize_session=False
    )
    db.query(Mistake).filter(Mistake.course_id == course_id).delete(
        synchronize_session=False
    )
    db.query(Question).filter(Question.course_id == course_id).delete(
        synchronize_session=False
    )
    db.query(QuizBatch).filter(QuizBatch.course_id == course_id).delete(
        synchronize_session=False
    )
    db.query(DocumentModel).filter(DocumentModel.course_id == course_id).delete(
        synchronize_session=False
    )
    # 会话历史随课程一起清理（聊天内容含隐私，不留下孤儿记录）
    db.query(ChatMessage).filter(ChatMessage.course_id == course_id).delete(
        synchronize_session=False
    )

    # 3. 删除课程
    db.delete(course)
    db.commit()
