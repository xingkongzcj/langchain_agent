"""复习计划服务。"""

import json
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.mistake import Mistake
from app.models.quiz import Question
from app.models.review import ReviewItem, ReviewPlan
from app.prompts.templates import build_review_plan_messages
from app.schemas.review import ReviewItemOut, ReviewPlanOut
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)

# 最大生成尝试次数（1 次初始 + 2 次重试）
MAX_ATTEMPTS = 3


def generate_review_plan(db: Session, course_id: int, name: str | None = None) -> ReviewPlan:
    """根据课程错题生成 7 天复习计划。"""
    # 1. 读取未掌握的错题
    mistakes = (
        db.query(Mistake)
        .filter(Mistake.course_id == course_id, Mistake.status == "unmastered")
        .all()
    )
    if not mistakes:
        raise BusinessException(code=400, message="没有需要复习的错题，请先答题")

    # 2. 提取错题信息（题目 + 解析）
    mistake_texts: list[str] = []
    for i, m in enumerate(mistakes, start=1):
        question = db.get(Question, m.question_id)
        if not question:
            continue
        mistake_texts.append(
            f"{i}. 题目：{question.question}\n   解析：{question.explanation or '无'}"
        )
    mistakes_text = "\n\n".join(mistake_texts)

    # 3. 调用 LLM 生成计划
    plan_data = _generate_plan_with_retry(mistakes_text)

    # 4. 写入 review_plans
    plan = ReviewPlan(
        course_id=course_id,
        name=plan_data.get("plan_name") or name or "7天复习计划",
        description=f"基于 {len(mistakes)} 道错题生成",
        status="active",
    )
    db.add(plan)
    db.flush()

    # 5. 写入 review_items（用 Python 计算真实日期）
    today = date.today()
    for item in plan_data.get("items", []):
        day = int(item.get("day", 1))
        review_date = today + timedelta(days=day - 1)
        db.add(
            ReviewItem(
                plan_id=plan.id,
                knowledge_point=str(item.get("knowledge_point", "")),
                review_date=review_date,
                completed=False,
            )
        )

    db.commit()
    db.refresh(plan)
    return plan


def _generate_plan_with_retry(mistakes_text: str) -> dict[str, Any]:
    """调用 LLM 生成复习计划并解析 JSON，失败重试。"""
    messages = build_review_plan_messages(mistakes_text)
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = get_chat_model().invoke(messages)
            content = response.content
            text = content if isinstance(content, str) else str(content)
            return _parse_plan_json(text)
        except Exception as exc:
            last_error = exc
            logger.warning("复习计划生成第 %d/%d 次失败: %s", attempt + 1, MAX_ATTEMPTS, exc)

    raise BusinessException(code=500, message=f"复习计划生成失败: {last_error}")


def _parse_plan_json(text: str) -> dict[str, Any]:
    """解析复习计划 JSON。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.lstrip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("复习计划不是 JSON 对象")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("复习计划缺少 items 字段或为空")
    return data


def list_review_plans(db: Session, course_id: int) -> list[ReviewPlan]:
    """获取课程下的复习计划列表。"""
    return (
        db.query(ReviewPlan)
        .filter(ReviewPlan.course_id == course_id)
        .order_by(ReviewPlan.id.desc())
        .all()
    )


def get_review_plan(db: Session, plan_id: int) -> ReviewPlanOut:
    """获取复习计划详情（含条目）。"""
    plan = db.get(ReviewPlan, plan_id)
    if not plan:
        raise BusinessException(code=404, message="复习计划不存在")

    items = (
        db.query(ReviewItem)
        .filter(ReviewItem.plan_id == plan_id)
        .order_by(ReviewItem.review_date.asc())
        .all()
    )

    return ReviewPlanOut(
        id=plan.id,
        course_id=plan.course_id,
        name=plan.name,
        description=plan.description,
        status=plan.status,
        created_at=plan.created_at,
        items=[ReviewItemOut.model_validate(i) for i in items],
    )


def update_review_item(db: Session, item_id: int, completed: bool) -> ReviewItem:
    """更新复习条目的完成状态。"""
    item = db.get(ReviewItem, item_id)
    if not item:
        raise BusinessException(code=404, message="复习条目不存在")
    item.completed = completed
    db.commit()
    db.refresh(item)
    return item
