"""课程管理路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.course import CourseCreate, CourseDetailOut, CourseListItem, CourseOut
from app.services import course_service

router = APIRouter(prefix="/api/courses", tags=["课程管理"])


@router.post("")
def create_course(data: CourseCreate, db: Session = Depends(get_db)) -> ApiResponse[CourseOut]:
    """创建课程。"""
    course = course_service.create_course(db, data)
    return ApiResponse.success(data=CourseOut.model_validate(course), message="课程创建成功")


@router.get("")
def list_courses(db: Session = Depends(get_db)) -> ApiResponse[list[CourseListItem]]:
    """获取课程列表。"""
    return ApiResponse.success(data=course_service.list_courses(db))


@router.get("/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)) -> ApiResponse[CourseDetailOut]:
    """获取课程详情。"""
    return ApiResponse.success(data=course_service.get_course(db, course_id))


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)) -> ApiResponse[None]:
    """删除课程（级联删除文档与向量）。"""
    course_service.delete_course(db, course_id)
    return ApiResponse.success(message="课程删除成功")
