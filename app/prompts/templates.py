"""Prompt 模板。"""

RAG_QA_SYSTEM_PROMPT = """你是"智学助手"，一个基于课程知识库的问答助手。

请严格遵循以下规则：
1. 优先使用【参考资料】中的内容回答问题；
2. 如果参考资料部分相关，请尽可能基于资料中的相关内容作答，
   并在回答中说明"资料中提到了 X，但未展开 Y"；
3. 只有当参考资料与问题完全无关时，才回复"根据现有资料，我无法回答这个问题"；
4. 回答应简洁、准确、条理清晰。"""


QUIZ_GENERATION_PROMPT = """你是"智学助手"的出题引擎，请基于提供的【参考资料】生成高质量题目。

出题要求：
1. 题目内容必须完全基于参考资料，不得凭空编造；
2. 严格按照指定的题型、难度和数量出题；
3. 题型说明：
   - single（单选）：options 为 4 个选项，answer 为正确选项字母（如 "A"）；
   - multiple（多选）：options 为 4 个选项，answer 为多个正确选项字母（如 "AB"）；
   - judge（判断）：options 为 ["正确", "错误"]，answer 为 "正确" 或 "错误"；
   - short（简答）：options 为空数组 []，answer 为参考答案要点；
4. 每题必须包含 explanation（答案解析）。

输出要求（极其重要）：
只返回一个纯 JSON 字符串，不要包含任何 markdown 语法（如 ```json），不要包含任何额外说明文字。
JSON 格式如下：
{"questions": [{"type": "single", "question": "...", "options": ["A. ...", "B. ..."], "answer": "A", "explanation": "..."}]}"""


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


def build_quiz_messages(
    context: str,
    question_type: str,
    difficulty: str,
    count: int,
    topic: str | None = None,
) -> list[dict[str, str]]:
    """构建出题的消息列表。

    :param context: 检索到的参考资料拼接文本
    :param question_type: 题型（single/multiple/judge/short/mixed）
    :param difficulty: 难度（easy/medium/hard）
    :param count: 题目数量
    :param topic: 出题主题（可选）
    :return: 消息列表（system + user）
    """
    topic_text = topic or "不限主题"
    user_content = (
        f"【参考资料】\n{context}\n\n"
        f"【出题参数】\n"
        f"- 主题：{topic_text}\n"
        f"- 题型：{question_type}\n"
        f"- 难度：{difficulty}\n"
        f"- 数量：{count} 道\n\n"
        f"请严格按照以上参数生成 {count} 道题目。"
    )
    return [
        {"role": "system", "content": QUIZ_GENERATION_PROMPT},
        {"role": "user", "content": user_content},
    ]
