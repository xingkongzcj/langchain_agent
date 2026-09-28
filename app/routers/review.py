"""复习计划路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.review import (
    ReviewItemOut,
    ReviewItemUpdate,
    ReviewPlanCreate,
    ReviewPlanOut,
)
from app.services import review_service

router = APIRouter(prefix="/api", tags=["复习计划"])


@router.post("/courses/{course_id}/review-plans")
def generate_review_plan(
    course_id: int,
    data: ReviewPlanCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[ReviewPlanOut]:
    """生成 7 天复习计划。"""
    plan = review_service.generate_review_plan(db, course_id, data.name)
    result = review_service.get_review_plan(db, plan.id)
    return ApiResponse.success(data=result, message="复习计划生成成功")


@router.get("/courses/{course_id}/review-plans")
def list_review_plans(
    course_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ReviewPlanOut]]:
    """获取复习计划列表。"""
    plans = review_service.list_review_plans(db, course_id)
    return ApiResponse.success(data=[ReviewPlanOut.model_validate(p) for p in plans])


@router.get("/review-plans/{plan_id}")
def get_review_plan(
    plan_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[ReviewPlanOut]:
    """获取复习计划详情（含条目）。"""
    return ApiResponse.success(data=review_service.get_review_plan(db, plan_id))


@router.patch("/review-items/{item_id}")
def update_review_item(
    item_id: int,
    data: ReviewItemUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[ReviewItemOut]:
    """标记复习条目完成/未完成。"""
    item = review_service.update_review_item(db, item_id, data.completed)
    return ApiResponse.success(data=ReviewItemOut.model_validate(item))
