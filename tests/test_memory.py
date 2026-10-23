"""会话记忆与学习画像的单元测试（纯函数，无需数据库 / API Key）。

运行：python -m pytest tests/test_memory.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prompts.templates import build_quiz_messages, build_rag_messages
from app.services import memory_service


# ============ L1：检索改写 ============

def test_rewrite_query_uses_previous_question_on_pronoun():
    """追问里的「它」要靠上一轮问题补全，否则检索不到内容。"""
    history = [
        {"role": "user", "content": "什么是 B+ 树"},
        {"role": "assistant", "content": "B+ 树是一种平衡多路查找树……"},
    ]
    rewritten = memory_service.rewrite_query("它和 B 树有什么区别", history)
    assert rewritten.startswith("什么是 B+ 树")
    assert "它和 B 树有什么区别" in rewritten


def test_rewrite_query_keeps_standalone_question():
    """完整独立的问题不应该被改写，避免污染检索。"""
    history = [{"role": "user", "content": "什么是 B+ 树"}]
    question = "请详细说明 MySQL 聚簇索引的存储结构差异"
    assert memory_service.rewrite_query(question, history) == question


def test_rewrite_query_without_history():
    """没有历史时原样返回。"""
    assert memory_service.rewrite_query("什么是 RAG", []) == "什么是 RAG"


def test_short_question_triggers_rewrite():
    """很短的问题大概率是追问。"""
    history = [{"role": "user", "content": "什么是向量数据库"}]
    assert memory_service.needs_rewrite("举个例子", history) is True


def test_needs_rewrite_without_user_message():
    """历史里只有 assistant 消息时不改写。"""
    history = [{"role": "assistant", "content": "……"}]
    assert memory_service.needs_rewrite("它是什么", history) is False


# ============ L2：学习画像 ============

def test_format_profile_empty_when_no_data():
    """没有任何数据时返回空串，避免给模型塞空信息。"""
    assert memory_service.format_profile([], 0, 0, 0) == ""


def test_format_profile_contains_weak_points_and_plan():
    text = memory_service.format_profile(
        ["RAG 的检索流程", "向量维度"], mastered_count=3, plan_total=7, plan_done=2
    )
    assert "薄弱知识点" in text
    assert "RAG 的检索流程" in text
    assert "已掌握错题：3 道" in text
    assert "共 7 条，已完成 2 条" in text


def test_format_profile_mastered_only():
    text = memory_service.format_profile([], mastered_count=2)
    assert "目前没有未掌握的错题" in text
    assert "已掌握错题：2 道" in text


# ============ Prompt 组装 ============

def test_build_rag_messages_with_history_and_profile():
    history = [
        {"role": "user", "content": "什么是 RAG"},
        {"role": "assistant", "content": "RAG 是检索增强生成"},
    ]
    messages = build_rag_messages(
        context="[参考资料 1]\nRAG 通过检索增强生成。",
        question="它有什么缺点",
        history=history,
        profile="【学生学习画像】\n- 薄弱知识点：RAG 的检索流程",
    )

    assert messages[0]["role"] == "system"
    assert "薄弱知识点" in messages[0]["content"]
    assert "历史回答可能不准确" in messages[0]["content"]
    # 历史消息按原顺序插在 system 与当前 user 之间
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[-1]["role"] == "user"
    assert "【参考资料】" in messages[-1]["content"]
    assert "它有什么缺点" in messages[-1]["content"]


def test_build_rag_messages_without_memory_is_single_turn():
    messages = build_rag_messages(context="ctx", question="问题")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_quiz_messages_injects_profile():
    messages = build_quiz_messages(
        context="ctx",
        question_type="single",
        difficulty="medium",
        count=3,
        profile="【学生学习画像】\n- 薄弱知识点：B+ 树",
    )
    assert "薄弱知识点" in messages[0]["content"]
    assert "提高这些内容的比重" in messages[0]["content"]
