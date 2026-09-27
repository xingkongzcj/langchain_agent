"""Prompt 模板。"""

RAG_QA_SYSTEM_PROMPT = """你是"智学助手"，一个基于课程知识库的问答助手。

请严格遵循以下规则：
1. 优先使用【参考资料】中的内容回答问题；
2. 如果参考资料部分相关，请尽可能基于资料中的相关内容作答，
   并在回答中说明"资料中提到了 X，但未展开 Y"；
3. 只有当参考资料与问题完全无关时，才回复"根据现有资料，我无法回答这个问题"；
4. 回答应简洁、准确、条理清晰。"""


def build_rag_messages(context: str, question: str) -> list[dict[str, str]]:
    """构建 RAG 问答的消息列表。

    :param context: 检索到的参考资料拼接文本
    :param question: 用户问题
    :return: 消息列表（system + user）
    """
    user_content = (
        f"【参考资料】\n{context}\n\n"
        f"【问题】\n{question}\n\n"
        "请根据以上参考资料回答问题。"
    )
    return [
        {"role": "system", "content": RAG_QA_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
