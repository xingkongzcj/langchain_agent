import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

# 1. 加载环境变量
load_dotenv()
api_key = os.getenv("SILICONFLOW_API_KEY")
api_base = os.getenv("SILICONFLOW_BASE_URL")

# 2. 初始化模型
model = init_chat_model(
    model="openai:Qwen/Qwen2.5-7B-Instruct",  # 换成你之前测试成功的模型
    api_key=api_key,
    base_url=api_base
)

# 3. 创建 Agent（暂时没有工具，相当于一个带系统提示词的聊天机器人）
agent = create_agent(
    model,
    tools=[],
    system_prompt="你是一个乐于助人的AI助手，请用四川话回答我的问题。"
)

# 4. 调用 Agent
response = agent.invoke({
    "messages": [{"role": "user", "content": "你好，你是谁？"}]
})

# 5. 打印结果（Agent返回的是字典，消息在 "messages" 键里）
print("AI回复:", response["messages"][-1].content)