"""文档上传、列表与删除路由。"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.db.mysql import get_db
from app.schemas.document import DocumentOut
from app.services import document_service

router = APIRouter(prefix="/api/courses", tags=["文档管理"])
documents_router = APIRouter(prefix="/api/documents", tags=["文档管理"])


@router.post("/{course_id}/documents")
async def upload_document(
    course_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse[DocumentOut]:
    """上传文档并入库。"""
    doc = await document_service.ingest_upload_file(db, course_id, file)
    return ApiResponse.success(data=DocumentOut.model_validate(doc), message="文档上传成功")


@router.get("/{course_id}/documents")
def list_documents(
    course_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[list[DocumentOut]]:
    """获取课程文档列表。"""
    docs = document_service.list_documents(db, course_id)
    return ApiResponse.success(data=[DocumentOut.model_validate(d) for d in docs])


@documents_router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除文档（同步删除 Chroma 向量与 MySQL 记录）。"""
    document_service.delete_document(db, document_id)
    return ApiResponse.success(message="文档删除成功")
