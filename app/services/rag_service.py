"""RAG 智能问答服务（含多轮会话记忆与学习画像）。"""

import logging

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BusinessException
from app.db.chroma import get_vectorstore
from app.prompts.templates import build_rag_messages
from app.schemas.chat import ChatResponse, Source
from app.services import memory_service
from app.services.llm import get_chat_model

# bge-m3 官方查询前缀（检索前增强 query 表示）
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

logger = logging.getLogger(__name__)


def retrieve_documents(
    course_id: int,
    query: str,
    top_k: int | None = None,
) -> list[Document]:
    """从课程知识库检索相关片段（公共方法，供问答与出题复用）。

    collection 按课程隔离 + metadata 双重过滤，防止跨课程串台。
    """
    vectorstore = get_vectorstore(f"course_{course_id}")
    query_with_prefix = f"{BGE_QUERY_PREFIX}{query}"
    return vectorstore.similarity_search(
        query_with_prefix,
        k=top_k or settings.top_k,
        filter={"course_id": course_id},  # type: ignore[arg-type]
    )


def chat_with_knowledge(
    db: Session,
    course_id: int,
    question: str,
    session_id: str | None = None,
) -> ChatResponse:
    """基于课程知识库的 RAG 问答（带多轮上下文）。

    :param db: 数据库会话（读写会话历史）
    :param course_id: 课程 ID
    :param question: 用户问题
    :param session_id: 会话 ID；为空则退化为单轮问答（不留历史）
    :return: 回答与引用来源
    """
    # 1. 读取历史；有历史时把追问补全成可检索的完整 query
    history = memory_service.load_history(db, course_id, session_id)
    search_query = memory_service.rewrite_query(question, history)

    # 2. 检索相关片段
    docs = retrieve_documents(course_id, search_query)
    if not docs:
        raise BusinessException(code=400, message="该课程知识库为空，请先上传文档")

    # 3. 拼接上下文 + 学习画像，构建 Prompt 并生成
    context = "\n\n".join(
        f"[参考资料 {index}]\n{doc.page_content}" for index, doc in enumerate(docs, start=1)
    )
    profile = memory_service.build_learning_profile(db, course_id)
    if profile:
        logger.info("已注入学习画像 course_id=%s", course_id)
    if search_query != question:
        logger.info("多轮检索改写 course_id=%s: %s", course_id, search_query[:80])
    messages = build_rag_messages(
        context=context,
        question=question,
        history=history,
        profile=profile,
    )
    response = get_chat_model().invoke(messages)
    content = response.content
    answer = content if isinstance(content, str) else str(content)

    # 4. 构造引用来源
    sources = [
        Source(filename=doc.metadata.get("filename", "未知"), text=doc.page_content)
        for doc in docs
    ]

    # 5. 写入会话历史（供下一轮指代消解与前端回显）
    memory_service.save_message(db, course_id, session_id, "user", question)
    memory_service.save_message(db, course_id, session_id, "assistant", answer)

    return ChatResponse(answer=answer, sources=sources)
