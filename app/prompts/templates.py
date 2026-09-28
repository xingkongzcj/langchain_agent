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


SHORT_ANSWER_GRADING_PROMPT = """你是"智学助手"的简答题批改引擎，请根据【参考答案】对用户的作答进行语义评分。

评分要求：
1. 只要用户作答的核心意思与参考答案一致（不要求逐字一致），即判为正确；
2. score 为 0-100 的整数，表示作答与参考答案的匹配程度；
3. reason 为简短的批改理由（一句话即可）。

输出要求（极其重要）：
仅返回纯 JSON，不要包含任何 markdown 标记或额外解释。格式如下：
{"correct": true, "score": 80, "reason": "..."}"""


def build_grading_messages(reference_answer: str, user_answer: str) -> list[dict[str, str]]:
    """构建简答题批改的消息列表。

    :param reference_answer: 参考答案
    :param user_answer: 用户作答
    :return: 消息列表（system + user）
    """
    user_content = (
        f"【参考答案】\n{reference_answer}\n\n"
        f"【用户作答】\n{user_answer}\n\n"
        "请对用户作答进行评分，并返回 JSON。"
    )
    return [
        {"role": "system", "content": SHORT_ANSWER_GRADING_PROMPT},
        {"role": "user", "content": user_content},
    ]


REVIEW_PLAN_PROMPT = """你是"智学助手"的复习计划引擎，请根据提供的【错题列表】制定一个 7 天复习计划。

要求：
1. 将错题涉及的知识点合理分配到 7 天内（第 1 天到第 7 天）；
2. 每个知识点只出现一次，不要重复；
3. 每天至少安排一个知识点（错题较少时可不连续安排）；
4. knowledge_point 为简洁的知识点描述（一句话即可）。

输出要求（极其重要）：
仅返回纯 JSON，不要包含任何 markdown 标记或额外解释。格式如下：
{"plan_name": "复习计划", "items": [{"day": 1, "knowledge_point": "RAG 的核心逻辑"}]}

注意：day 字段必须是 1-7 的整数，表示第几天；不要计算具体日期。"""


def build_review_plan_messages(mistakes_text: str) -> list[dict[str, str]]:
    """构建复习计划生成的消息列表。

    :param mistakes_text: 错题拼接文本
    :return: 消息列表（system + user）
    """
    user_content = (
        f"【错题列表】\n{mistakes_text}\n\n"
        "请根据以上错题制定 7 天复习计划，并返回 JSON。"
    )
    return [
        {"role": "system", "content": REVIEW_PLAN_PROMPT},
        {"role": "user", "content": user_content},
    ]
