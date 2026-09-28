"""LLM 模型初始化模块。"""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    """懒加载 Chat 模型（通过 SiliconFlow OpenAI 兼容接口）。"""
    return init_chat_model(
        model=f"openai:{settings.llm_model}",
        api_key=settings.siliconflow_api_key,
        base_url=settings.siliconflow_base_url,
    )
