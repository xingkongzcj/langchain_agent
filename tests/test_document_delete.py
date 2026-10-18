"""删除文档业务逻辑的单元测试（mock 掉数据库与向量库，无需 MySQL / API Key）。

运行：python -m pytest tests/test_document_delete.py -v
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.exceptions import BusinessException
from app.services import document_service


def test_delete_document_not_found():
    """文档不存在时抛 404，且不触碰向量库。"""
    db = MagicMock()
    db.get.return_value = None

    try:
        document_service.delete_document(db, 999)
    except BusinessException as exc:
        assert exc.code == 404
    else:
        raise AssertionError("文档不存在时应抛出 BusinessException")


def test_delete_document_removes_vectors_and_record(monkeypatch):
    """正常删除：按 document_id 删向量，再删 MySQL 记录。"""
    doc = SimpleNamespace(id=7, course_id=3, filename="a.md")

    db = MagicMock()
    db.get.return_value = doc

    vectorstore = MagicMock()
    monkeypatch.setattr(document_service, "get_vectorstore", lambda name: vectorstore)

    document_service.delete_document(db, 7)

    vectorstore._collection.delete.assert_called_once_with(where={"document_id": 7})
    db.delete.assert_called_once_with(doc)
    assert db.commit.called


def test_delete_document_vector_failure_keeps_record(monkeypatch):
    """向量删除失败时不删记录，避免产生幽灵数据。"""
    doc = SimpleNamespace(id=8, course_id=3, filename="b.md")

    db = MagicMock()
    db.get.return_value = doc

    vectorstore = MagicMock()
    vectorstore._collection.delete.side_effect = RuntimeError("chroma down")
    monkeypatch.setattr(document_service, "get_vectorstore", lambda name: vectorstore)

    try:
        document_service.delete_document(db, 8)
    except BusinessException as exc:
        assert exc.code == 500
    else:
        raise AssertionError("向量删除失败时应抛出 BusinessException")

    assert not db.delete.called
    assert not db.commit.called
