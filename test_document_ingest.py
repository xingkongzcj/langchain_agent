"""测试文档入库（本地文件路径方式）。

前提：
1. MySQL 已启动：docker-compose up -d
2. .env 已配置有效的 SILICONFLOW_API_KEY

用法：python test_document_ingest.py
"""

import os

from app.config import settings
from app.db.mysql import SessionLocal, init_db
from app.models.course import Course
from app.services.document_service import ingest_document


def main() -> None:
    if not settings.siliconflow_api_key:
        print("[错误] 请在 .env 中配置 SILICONFLOW_API_KEY 后再运行。")
        return

    # 1. 建表（确保表存在）
    init_db()

    # 2. 准备测试文档
    sample_file = "test_sample.txt"
    sample_content = (
        "RAG 是检索增强生成（Retrieval-Augmented Generation）的缩写。\n"
        "RAG 通过先从知识库检索相关片段，再结合大模型生成回答，从而降低幻觉。\n"
        "FastAPI 是一款高性能的 Python Web 框架，支持异步处理和自动生成 API 文档。\n"
        "LangChain 是用于构建大语言模型应用的编排框架，提供文档加载、切分、向量库等抽象。\n"
        "Chroma 是一款轻量级的本地向量数据库，适合快速原型开发。\n"
    )
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_content)

    db = SessionLocal()
    try:
        # 3. 创建测试课程
        course = Course(name="测试课程", description="用于测试文档入库")
        db.add(course)
        db.commit()
        db.refresh(course)
        print(f"[成功] 已创建课程: id={course.id}, name={course.name}")

        # 4. 入库
        doc = ingest_document(
            db=db,
            course_id=course.id,
            file_path=sample_file,
            filename=sample_file,
            file_type="txt",
            file_size=os.path.getsize(sample_file),
        )
        print(
            f"[成功] 文档入库完成: id={doc.id}, filename={doc.filename}, "
            f"chunk_count={doc.chunk_count}, status={doc.status}"
        )
    finally:
        db.close()
        # 清理测试文件
        if os.path.exists(sample_file):
            os.remove(sample_file)


if __name__ == "__main__":
    main()
