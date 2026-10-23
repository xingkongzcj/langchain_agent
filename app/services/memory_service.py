"""会话记忆：L1 多轮上下文 + L2 学习画像。

L1（会话短期记忆）
    把每轮问答存进 chat_messages，按 (course_id, session_id) 取最近若干轮拼进 Prompt；
    检索前再做一次启发式「指代消解」，否则「它和 B+ 树有什么区别」这类追问检索不到内容。

L2（学习记忆）
    从错题本与复习计划聚合出「学生学习画像」，注入问答和出题 Prompt，
    让回答与题目能照顾到真实薄弱点，而不是每次从零开始。
"""

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage
from app.models.mistake import Mistake
from app.models.quiz import Question
from app.models.review import ReviewItem, ReviewPlan

logger = logging.getLogger(__name__)

# ---- L1 参数 ----
MAX_HISTORY_TURNS = 6  # 最多带几轮（1 轮 = 1 问 + 1 答）
MAX_HISTORY_CHARS = 4000  # 历史字符预算，超出从最旧的丢
MAX_SESSION_MESSAGES = 50  # 回显给前端时最多返回多少条

# 指代词：出现这些词时把上一轮问题拼进检索 query
PRONOUN_HINTS = (
    "它",
    "这个",
    "那个",
    "上述",
    "上面",
    "刚才",
    "前面",
    "这种",
    "这些",
    "该",
    "此",
)
SHORT_QUESTION_LEN = 8  # 过短的问题大概率是追问

# ---- L2 参数 ----
MAX_WEAK_POINTS = 6
QUESTION_PREVIEW = 40


# ============ L1：会话历史 ============

def load_history(
    db: Session,
    course_id: int,
    session_id: str | None,
    max_turns: int = MAX_HISTORY_TURNS,
) -> list[dict[str, str]]:
    """读取最近若干轮对话（按时间正序返回，超出字符预算时丢最旧的）。"""
    if not session_id:
        return []

    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.course_id == course_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.id.desc())
        .limit(max_turns * 2)
        .all()
    )
    if not rows:
        return []
    rows.reverse()

    # 字符预算：从最新的往前累加，超预算就停
    kept: list[ChatMessage] = []
    total = 0
    for row in reversed(rows):
        if kept and total + len(row.content) > MAX_HISTORY_CHARS:
            break
        kept.append(row)
        total += len(row.content)
    kept.reverse()

    return [{"role": row.role, "content": row.content} for row in kept]


def save_message(
    db: Session,
    course_id: int,
    session_id: str | None,
    role: str,
    content: str,
) -> None:
    """写入一条会话消息（session_id 为空表示不留痕，直接跳过）。"""
    if not session_id:
        return
    db.add(
        ChatMessage(
            course_id=course_id,
            session_id=session_id,
            role=role,
            content=content,
        )
    )
    db.commit()


def list_session_messages(
    db: Session,
    course_id: int,
    session_id: str,
    limit: int = MAX_SESSION_MESSAGES,
) -> list[dict[str, str]]:
    """取会话消息用于前端回显（时间正序）。"""
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.course_id == course_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content} for row in rows]


def clear_session(db: Session, course_id: int, session_id: str) -> int:
    """清空某个会话（隐私要求：用户可随时删除聊天记录）。"""
    deleted = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.course_id == course_id,
            ChatMessage.session_id == session_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info("已清空会话 course_id=%s session_id=%s 消息数=%s", course_id, session_id, deleted)
    return int(deleted or 0)


# ============ L1：检索改写 ============

def _last_user_question(history: list[dict[str, str]]) -> str:
    for message in reversed(history):
        if message["role"] == "user":
            return message["content"]
    return ""


def needs_rewrite(question: str, history: list[dict[str, str]]) -> bool:
    """判断当前问题是否依赖上一轮上下文（含指代词，或本身很短）。"""
    if not history:
        return False
    if not _last_user_question(history):
        return False

    text = (question or "").strip()
    if len(text) <= SHORT_QUESTION_LEN:
        return True
    return any(hint in text for hint in PRONOUN_HINTS)


def rewrite_query(question: str, history: list[dict[str, str]]) -> str:
    """把追问补全成可检索的完整 query。

    例：上一轮问"什么是 B+ 树"，本轮问"它和 B 树有什么区别"，
        改写为"什么是 B+ 树 它和 B 树有什么区别"，bge-m3 才能检索到相关内容。
    """
    if not needs_rewrite(question, history):
        return question
    return f"{_last_user_question(history)} {question}"


# ============ L2：学习画像 ============

def _shorten(text: str | None) -> str:
    """题目文本压成一句短知识点（去掉换行、超长截断）。"""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= QUESTION_PREVIEW:
        return cleaned
    return cleaned[:QUESTION_PREVIEW] + "…"


def build_learning_profile(db: Session, course_id: int) -> str:
    """聚合错题与复习计划，生成注入 Prompt 的学习画像（无数据时返回空串）。"""
    weak_rows = (
        db.query(Question.question)
        .join(Mistake, Mistake.question_id == Question.id)
        .filter(
            Mistake.course_id == course_id,
            Mistake.status == "unmastered",
        )
        .order_by(Mistake.id.desc())
        .limit(MAX_WEAK_POINTS)
        .all()
    )
    weak_points = [_shorten(text) for (text,) in weak_rows if text]

    mastered_count = int(
        db.query(func.count(Mistake.id))
        .filter(Mistake.course_id == course_id, Mistake.status == "mastered")
        .scalar()
        or 0
    )

    plan_total = 0
    plan_done = 0
    plan = (
        db.query(ReviewPlan)
        .filter(ReviewPlan.course_id == course_id)
        .order_by(ReviewPlan.id.desc())
        .first()
    )
    if plan:
        plan_total = int(
            db.query(func.count(ReviewItem.id))
            .filter(ReviewItem.plan_id == plan.id)
            .scalar()
            or 0
        )
        plan_done = int(
            db.query(func.count(ReviewItem.id))
            .filter(ReviewItem.plan_id == plan.id, ReviewItem.completed.is_(True))
            .scalar()
            or 0
        )

    return format_profile(weak_points, mastered_count, plan_total, plan_done)


def format_profile(
    weak_points: list[str],
    mastered_count: int,
    plan_total: int = 0,
    plan_done: int = 0,
) -> str:
    """把统计结果格式化成画像文本（纯函数，便于单测）。

    没有任何数据时返回空串，调用方据此跳过注入，避免给模型塞空信息。
    """
    if not weak_points and not mastered_count and not plan_total:
        return ""

    lines = ["【学生学习画像】"]
    if weak_points:
        lines.append(
            "- 薄弱知识点（未掌握错题，答疑与出题请优先照顾）："
            + "、".join(weak_points)
        )
    else:
        lines.append("- 目前没有未掌握的错题")
    if mastered_count:
        lines.append(f"- 已掌握错题：{mastered_count} 道")
    if plan_total:
        lines.append(f"- 当前复习计划：共 {plan_total} 条，已完成 {plan_done} 条")
    return "\n".join(lines)
