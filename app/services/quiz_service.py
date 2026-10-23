"""自动出题服务。"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BusinessException
from app.models.quiz import Question, QuizBatch
from app.prompts.templates import build_quiz_messages
from app.services import memory_service
from app.services.llm import get_chat_model
from app.services.rag_service import retrieve_documents

logger = logging.getLogger(__name__)

# 最大生成尝试次数（1 次初始 + 2 次重试）
MAX_ATTEMPTS = 3


def generate_quiz(
    db: Session,
    course_id: int,
    topic: str | None,
    question_type: str,
    difficulty: str,
    count: int,
) -> QuizBatch:
    """基于课程知识库生成题目并入库。

    :param db: 数据库会话
    :param course_id: 课程 ID
    :param topic: 出题主题（可选）
    :param question_type: 题型（single/multiple/judge/short/mixed）
    :param difficulty: 难度（easy/medium/hard）
    :param count: 题目数量
    :return: 出题批次
    """
    # 1. 检索相关片段
    query = topic or "课程核心知识点"
    docs = retrieve_documents(course_id, query, top_k=settings.top_k)
    if not docs:
        raise BusinessException(code=400, message="该课程知识库为空，请先上传文档")

    context = "\n\n".join(
        f"[片段 {index}]\n{doc.page_content}" for index, doc in enumerate(docs, start=1)
    )

    # 2. 构建 Prompt（注入学习画像：薄弱知识点提高出题比重）
    profile = memory_service.build_learning_profile(db, course_id)
    messages = build_quiz_messages(
        context=context,
        topic=topic,
        question_type=question_type,
        difficulty=difficulty,
        count=count,
        profile=profile,
    )

    # 3. 生成并解析（带重试）
    questions = _generate_with_retry(messages, count)

    # 4. 入库：先写出题批次，再批量写题目
    batch = QuizBatch(
        course_id=course_id,
        topic=topic,
        question_type=question_type,
        difficulty=difficulty,
        count=len(questions),
    )
    db.add(batch)
    db.flush()  # 获取 batch.id

    for q in questions:
        db.add(
            Question(
                batch_id=batch.id,
                course_id=course_id,
                type=q.get("type", "single"),
                question=q.get("question", ""),
                options=q.get("options"),
                answer=q.get("answer"),
                explanation=q.get("explanation"),
            )
        )

    db.commit()
    db.refresh(batch)
    return batch


def _generate_with_retry(messages: list[dict[str, str]], count: int) -> list[dict[str, Any]]:
    """调用 LLM 生成题目并解析 JSON，解析失败时重试（最多 2 次）。"""
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = get_chat_model().invoke(messages)
            content = response.content
            text = content if isinstance(content, str) else str(content)
            return _parse_quiz_json(text, count)
        except Exception as exc:
            last_error = exc
            logger.warning("出题生成第 %d/%d 次失败: %s", attempt + 1, MAX_ATTEMPTS, exc)

    raise BusinessException(code=500, message=f"题目生成失败: {last_error}")


def _parse_quiz_json(text: str, count: int) -> list[dict[str, Any]]:
    """解析 LLM 返回的 JSON，提取题目列表。"""
    cleaned = _strip_markdown_fence(text)
    data = json.loads(cleaned)
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("解析结果中缺少 questions 字段或为空")
    return questions[:count]


def _strip_markdown_fence(text: str) -> str:
    """去除 LLM 输出可能包裹的 markdown 代码块标记。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.lstrip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def list_questions(db: Session, course_id: int, batch_id: int | None = None) -> list[Question]:
    """获取课程下的题目列表，可按批次筛选。"""
    query = db.query(Question).filter(Question.course_id == course_id)
    if batch_id is not None:
        query = query.filter(Question.batch_id == batch_id)
    return query.order_by(Question.id.asc()).all()
