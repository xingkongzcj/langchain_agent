"""Prompt 模板。"""

RAG_QA_SYSTEM_PROMPT = """你是"智学助手"，一个基于课程知识库的问答助手。

请严格遵循以下规则：
1. 仅根据用户提供的【参考资料】回答问题，不要使用外部知识或你的记忆；
2. 如果参考资料中找不到答案，请明确回复"根据现有资料，我无法回答这个问题"，严禁编造；
3. 回答应简洁、准确、条理清晰。"""


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
