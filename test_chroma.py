"""验证 Chroma 本地向量写入与检索。

运行前请确保 .env 中已配置有效的 SILICONFLOW_API_KEY。
用法：python test_chroma.py
"""

from app.config import settings
from app.db.chroma import get_vectorstore


def main() -> None:
    if not settings.siliconflow_api_key:
        print("[错误] 请在 .env 中配置 SILICONFLOW_API_KEY 后再运行。")
        return

    collection_name = "test_chroma"
    print(f"Embedding 模型: {settings.embedding_model}")
    print(f"持久化目录: {settings.chroma_persist_dir}")

    # 初始化向量库
    vectorstore = get_vectorstore(collection_name)

    # 写入测试文本
    texts = [
        "RAG 是检索增强生成（Retrieval-Augmented Generation）的缩写。",
        "FastAPI 是一款高性能的 Python Web 框架。",
        "LangChain 是用于构建大语言模型应用的编排框架。",
        "Chroma 是一款轻量级的本地向量数据库。",
    ]
    metadatas = [{"source": f"demo_{i}"} for i in range(len(texts))]
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    print(f"[成功] 已写入 {len(texts)} 条文本向量。")

    # 检索验证
    query = "什么是检索增强生成？"
    results = vectorstore.similarity_search(query, k=2)
    print(f"\n查询：{query}")
    print("检索结果：")
    for i, doc in enumerate(results, start=1):
        print(f"  {i}. {doc.page_content}")

    if results:
        print("\n[通过] Chroma 本地写入与检索验证成功。")
    else:
        print("\n[失败] 未检索到结果。")


if __name__ == "__main__":
    main()
