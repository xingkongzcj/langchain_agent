"""Chroma 向量库初始化模块。"""

import logging

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


def get_embeddings() -> OpenAIEmbeddings:
    """获取 Embedding 模型（通过 SiliconFlow OpenAI 兼容接口调用 BAAI/bge-m3）。"""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.siliconflow_api_key,
        base_url=settings.siliconflow_base_url,
    )


def get_vectorstore(collection_name: str) -> Chroma:
    """初始化并返回 Chroma 向量库实例。

    :param collection_name: collection 名称（如 course_1）
    :return: Chroma 向量库实例
    """
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def check_chroma() -> bool:
    """检查 Chroma 是否可访问（能否初始化并访问 collection）。"""
    try:
        vectorstore = get_vectorstore("health_check")
        vectorstore._collection.count()
        return True
    except Exception:
        return False


def delete_collection(collection_name: str) -> None:
    """删除指定名称的 Chroma collection（不存在则忽略）。"""
    try:
        vectorstore = get_vectorstore(collection_name)
        vectorstore._client.delete_collection(collection_name)
        logger.info("已删除 Chroma collection: %s", collection_name)
    except Exception as exc:
        logger.warning("删除 Chroma collection %s 失败: %s", collection_name, exc)
