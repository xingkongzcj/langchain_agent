"""错题本服务：判题、错题记录与复习管理。"""

import json
import logging
import re

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models.mistake import Mistake
from app.models.quiz import Question
from app.prompts.templates import build_grading_messages
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)

# 关键词匹配阈值（用户答案包含参考答案 60% 关键词即视为正确）
KEYWORD_MATCH_THRESHOLD = 0.6


def submit_answer(db: Session, question_id: int, user_answer: str) -> dict:
    """提交答案并判题，答错自动写入错题本。"""
    question = db.get(Question, question_id)
    if not question:
        raise BusinessException(code=404, message="题目不存在")

    result = _grade(question, user_answer)
    result["correct_answer"] = question.answer
    result["explanation"] = question.explanation

    if result["correct"]:
        result["mistake_id"] = None
    else:
        mistake = _record_mistake(db, question, user_answer)
        result["mistake_id"] = mistake.id if mistake else None

    return result


def _grade(question: Question, user_answer: str) -> dict:
    """判题：客观题字符串比对，简答题 LLM 语义打分。"""
    if question.type == "short":
        return _grade_short_answer(question, user_answer)
    return {"correct": _grade_objective(question, user_answer)}


def _grade_objective(question: Question, user_answer: str) -> bool:
    """客观题判分：单选/判断直接比对，多选排序后比对。"""
    if question.type == "multiple":
        return _normalize(user_answer) == _normalize(question.answer)
    return (user_answer or "").strip() == (question.answer or "").strip()


def _normalize(text: str | None) -> str:
    """对答案字符串排序，处理多选顺序问题（ABCD 与 DCBA 等价）。"""
    return "".join(sorted((text or "").strip()))


def _grade_short_answer(question: Question, user_answer: str) -> dict:
    """简答题判分：LLM 语义打分，失败降级为关键词匹配。"""
    reference = question.answer or ""
    llm_raw: str | None = None

    # 1. 尝试 LLM 语义打分
    try:
        messages = build_grading_messages(reference, user_answer)
        response = get_chat_model().invoke(messages)
        content = response.content
        text = content if isinstance(content, str) else str(content)
        llm_raw = text
        data = _parse_grading_json(text)
        return {
            "correct": bool(data.get("correct")),
            "score": int(data.get("score", 0)),
            "reason": str(data.get("reason", "")),
        }
    except Exception as exc:
        logger.warning("简答题 LLM 打分失败，降级为关键词匹配: %s", exc)

    # 2. 降级：关键词匹配
    keywords = _extract_keywords(reference)
    if keywords:
        matched = sum(1 for kw in keywords if kw in user_answer)
        correct = (matched / len(keywords)) >= KEYWORD_MATCH_THRESHOLD
        return {
            "correct": correct,
            "score": 100 if correct else 0,
            "reason": "LLM 打分失败，已降级为关键词匹配",
            "llm_raw": llm_raw,
        }

    # 3. 关键词匹配也无法判断：默认判错（待复习）
    return {
        "correct": False,
        "score": 0,
        "reason": "无法自动判分，已记为待复习",
        "llm_raw": llm_raw,
    }


def _parse_grading_json(text: str) -> dict:
    """解析简答题批改 JSON。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.lstrip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("批改结果不是 JSON 对象")
    return data


def _extract_keywords(text: str) -> list[str]:
    """从参考答案中提取关键词（按标点切分短语）。"""
    parts = re.split(r"[,，。；;、！？!?\s]+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def _record_mistake(db: Session, question: Question, user_answer: str) -> Mistake | None:
    """答错时写入错题本（同一题已存在未掌握记录则不重复插入）。"""
    existing = (
        db.query(Mistake)
        .filter(Mistake.question_id == question.id, Mistake.status == "unmastered")
        .first()
    )
    if existing:
        return existing

    mistake = Mistake(
        course_id=question.course_id,
        question_id=question.id,
        user_answer=user_answer,
        status="unmastered",
        review_count=0,
    )
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    return mistake


def list_mistakes(db: Session, course_id: int, status: str | None = None) -> list[dict]:
    """获取错题本列表（含题干与正确答案）。"""
    query = (
        db.query(Mistake, Question)
        .join(Question, Question.id == Mistake.question_id)
        .filter(Mistake.course_id == course_id)
    )
    if status:
        query = query.filter(Mistake.status == status)
    rows = query.order_by(Mistake.id.desc()).all()

    return [
        {
            "id": mistake.id,
            "question_id": mistake.question_id,
            "question": question.question,
            "user_answer": mistake.user_answer,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "status": mistake.status,
            "review_count": mistake.review_count,
            "created_at": mistake.created_at,
        }
        for mistake, question in rows
    ]


def update_mistake(db: Session, mistake_id: int, status: str) -> Mistake:
    """更新错题状态（标记掌握/未掌握）。"""
    mistake = db.get(Mistake, mistake_id)
    if not mistake:
        raise BusinessException(code=404, message="错题记录不存在")
    mistake.status = status
    db.commit()
    db.refresh(mistake)
    return mistake


def delete_mistake(db: Session, mistake_id: int) -> None:
    """移除错题记录。"""
    mistake = db.get(Mistake, mistake_id)
    if not mistake:
        raise BusinessException(code=404, message="错题记录不存在")
    db.delete(mistake)
    db.commit()
