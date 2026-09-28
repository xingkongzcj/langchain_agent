"""验证 Markdown 两层切分效果。

用法：python tests/test_split_markdown.py

读取 tests/data/test_knowledge.md，打印 chunk 总数，
以及每个 chunk 的前 50 字 + metadata 中的 h1/h2。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_community.document_loaders import TextLoader

from app.services.document_service import split_documents

# 测试数据目录（tests/data）
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    file_path = str(DATA_DIR / "test_knowledge.md")
    if not os.path.exists(file_path):
        print(f"[错误] 未找到 {file_path}，请确认测试数据文件存在。")
        return

    # 读取原始 Markdown（保留 # 标题语法）
    raw_docs = TextLoader(file_path, encoding="utf-8").load()
    if not raw_docs:
        print(f"[错误] {file_path} 内容为空。")
        return

    # 两层切分
    chunks = split_documents(raw_docs, "md")

    print(f"chunk 总数: {len(chunks)}\n")
    for index, chunk in enumerate(chunks):
        preview = chunk.page_content[:50].replace("\n", " ")
        h1 = chunk.metadata.get("h1", "")
        h2 = chunk.metadata.get("h2", "")
        print(f"[{index}] h1={h1!r} h2={h2!r}")
        print(f"      {preview}...")
        print()


if __name__ == "__main__":
    main()
