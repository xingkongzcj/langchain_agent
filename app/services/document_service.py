"""文档入库服务：解析、切分、向量化。"""

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredFileLoader,
    UnstructuredPDFLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.db.chroma import get_vectorstore
from app.models.document import Document as DocumentModel

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt"}

# 切分参数
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Markdown 标题切分规则
MARKDOWN_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def _select_loader(file_path: str) -> BaseLoader:
    """根据文件扩展名选择合适的文档 Loader。

    注意：Markdown 使用 TextLoader 保留原始 # 标题语法，
    以便 MarkdownHeaderTextSplitter 正确识别章节层级。
    """
    ext = Path(file_path).suffix.lower()
    if ext in {".txt", ".md"}:
        return TextLoader(file_path, encoding="utf-8")
    if ext == ".pdf":
        return UnstructuredPDFLoader(file_path)
    if ext in {".docx", ".doc"}:
        return UnstructuredWordDocumentLoader(file_path)
    # 兜底：通用 Unstructured Loader
    return UnstructuredFileLoader(file_path)


def _split_markdown(raw_docs: list[LangchainDocument]) -> list[LangchainDocument]:
    """Markdown 两层切分：先按标题切，再按长度兜底切分。"""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=MARKDOWN_HEADERS,
        strip_headers=False,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks: list[LangchainDocument] = []
    for raw_doc in raw_docs:
        # 第一层：按标题切分，块带 h1/h2/h3 metadata
        header_splits = header_splitter.split_text(raw_doc.page_content)
        # 第二层：对每个章节块按长度兜底切分（保留标题 metadata）
        for header_split in header_splits:
            chunks.extend(text_splitter.split_documents([header_split]))
    return chunks


def _split_generic(raw_docs: list[LangchainDocument]) -> list[LangchainDocument]:
    """通用切分（PDF / Word / TXT）。"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return text_splitter.split_documents(raw_docs)


def split_documents(
    raw_docs: list[LangchainDocument],
    file_type: str,
) -> list[LangchainDocument]:
    """按文件类型选择切分策略。"""
    if file_type == "md":
        return _split_markdown(raw_docs)
    return _split_generic(raw_docs)


def _build_metadata(
    chunk: LangchainDocument,
    index: int,
    course_id: int,
    document_id: int,
    filename: str,
) -> dict[str, Any]:
    """构建单个 chunk 的 metadata（保留 source 与章节标题）。"""
    meta: dict[str, Any] = {
        "course_id": course_id,
        "document_id": document_id,
        "chunk_index": index,
        "filename": filename,
        "source": filename,
    }
    # 保留章节标题（仅 Markdown 文件有 h1/h2/h3）
    for header_key in ("h1", "h2", "h3"):
        value = chunk.metadata.get(header_key)
        if value:
            meta[header_key] = value
    return meta


def ingest_document(
    db: Session,
    course_id: int,
    file_path: str,
    filename: str,
    file_type: str,
    file_size: int | None = None,
) -> DocumentModel:
    """文档入库：解析 -> 切分 -> 向量化 -> 写库。

    :param db: 数据库会话
    :param course_id: 课程 ID
    :param file_path: 本地文件路径
    :param filename: 原始文件名
    :param file_type: 扩展名（不含点，如 pdf/docx/md/txt）
    :param file_size: 文件大小（字节）
    :return: 入库后的文档记录
    """
    # 1. 创建文档记录（status=processing）
    doc = DocumentModel(
        course_id=course_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        chunk_count=0,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # 2. 解析文档
        loader = _select_loader(file_path)
        raw_docs = loader.load()
        if not raw_docs:
            raise BusinessException(code=400, message="文档内容为空，无法入库")

        # 3. 切分文档（Markdown 走两层切分，其余走通用切分）
        chunks = split_documents(raw_docs, file_type)
        if not chunks:
            raise BusinessException(code=400, message="文档切分后无有效内容")

        # 4. 向量化存储到 Chroma
        vectorstore = get_vectorstore(f"course_{course_id}")
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [
            _build_metadata(chunk, index, course_id, doc.id, filename)
            for index, chunk in enumerate(chunks)
        ]
        vectorstore.add_texts(texts=texts, metadatas=metadatas)

        # 5. 更新文档状态为已完成
        doc.chunk_count = len(chunks)
        doc.status = "completed"
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as exc:
        # 解析/向量化失败，标记失败并抛出业务异常
        doc.status = "failed"
        doc.error = str(exc)
        db.commit()
        db.refresh(doc)
        raise BusinessException(code=500, message=f"文档入库失败: {exc}") from exc


async def ingest_upload_file(
    db: Session,
    course_id: int,
    upload_file: UploadFile,
) -> DocumentModel:
    """处理 FastAPI 上传的文件并入库。

    :param db: 数据库会话
    :param course_id: 课程 ID
    :param upload_file: FastAPI 上传的文件对象
    :return: 入库后的文档记录
    """
    filename = upload_file.filename or "unnamed"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise BusinessException(code=400, message=f"不支持的文件类型: {ext or '未知'}")

    content = await upload_file.read()

    # 保存到临时文件（Loader 需要文件路径）
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(content)

    try:
        return ingest_document(
            db=db,
            course_id=course_id,
            file_path=tmp_path,
            filename=filename,
            file_type=ext.lstrip("."),
            file_size=len(content),
        )
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def list_documents(db: Session, course_id: int) -> list[DocumentModel]:
    """获取课程下的文档列表。"""
    return (
        db.query(DocumentModel)
        .filter(DocumentModel.course_id == course_id)
        .order_by(DocumentModel.id.desc())
        .all()
    )
