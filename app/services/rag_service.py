"""RAG 智能问答服务。"""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings
from app.core.exceptions import BusinessException
from app.db.chroma import get_vectorstore
from app.prompts.templates import build_rag_messages
from app.schemas.chat import ChatResponse, Source

# bge-m3 官方查询前缀（检索前增强 query 表示）
BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


@lru_cache
def _get_chat_model() -> BaseChatModel:
    """懒加载 Chat 模型（通过 SiliconFlow OpenAI 兼容接口）。"""
    return init_chat_model(
        model=f"openai:{settings.llm_model}",
        api_key=settings.siliconflow_api_key,
        base_url=settings.siliconflow_base_url,
    )


def chat_with_knowledge(
    course_id: int,
    question: str,
    session_id: str | None = None,
) -> ChatResponse:
    """基于课程知识库的 RAG 问答。

    当前为无状态问答（session_id 暂未用于会话记忆，每次提问独立）。

    :param course_id: 课程 ID
    :param question: 用户问题
    :param session_id: 会话 ID（预留，暂未使用）
    :return: 回答与引用来源
    """
    # 1. 检索（collection 按课程隔离 + metadata 双重过滤，防止跨课程串台）
    # bge-m3 官方建议：检索前给查询加前缀，提升 query 表示质量
    vectorstore = get_vectorstore(f"course_{course_id}")
    query_with_prefix = f"{BGE_QUERY_PREFIX}{question}"
    docs = vectorstore.similarity_search(
        query_with_prefix,
        k=settings.top_k,
        filter={"course_id": course_id},  # type: ignore[arg-type]
    )

    if not docs:
        raise BusinessException(code=400, message="该课程知识库为空，请先上传文档")

    # 2. 拼接上下文
    context = "\n\n".join(
        f"[参考资料 {index}]\n{doc.page_content}" for index, doc in enumerate(docs, start=1)
    )

    # 3. 构建 Prompt 并生成
    messages = build_rag_messages(context=context, question=question)
    response = _get_chat_model().invoke(messages)
    content = response.content
    answer = content if isinstance(content, str) else str(content)

    # 4. 构造引用来源
    sources = [
        Source(filename=doc.metadata.get("filename", "未知"), text=doc.page_content)
        for doc in docs
    ]

    return ChatResponse(answer=answer, sources=sources)
