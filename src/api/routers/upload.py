"""模块12 上传路由 — POST /api/upload"""

import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.deps import get_pipeline, get_store
from src.api.models import UploadRequest, UploadResponse
from src.embedding.milvus_store import MilvusStore
from src.embedding.pipeline import IndexingPipeline
from src.ingestion.router import parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["上传"])


@router.post("/upload", response_model=UploadResponse)
async def upload_by_path(
    req: UploadRequest,
    pipeline: IndexingPipeline = Depends(get_pipeline),
) -> UploadResponse:
    """通过文件路径上传 — 解析 → 分块 → 向量化 → 入库

    适用于本地文件或 URL。
    """
    t0 = time.time()

    try:
        parse_result = parse_file(req.file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}")

    if not parse_result.markdown:
        return UploadResponse(
            status="failed",
            source_file=req.file_path,
            errors=parse_result.errors or ["解析结果为空"],
            elapsed_seconds=round(time.time() - t0, 1),
        )

    result = pipeline.run_from_text(
        text=parse_result.markdown,
        source_file=req.file_path,
        doc_type=parse_result.document.doc_type,
        recreate_collection=req.recreate_collection,
    )

    return UploadResponse(
        status=result["status"],
        source_file=req.file_path,
        total_chunks=result.get("total_chunks", 0),
        embedded=result.get("embedded", 0),
        inserted=result.get("inserted", 0),
        elapsed_seconds=result.get("elapsed_seconds", 0),
        errors=result.get("errors", []),
    )


@router.post("/upload/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    recreate_collection: bool = Form(False),
    pipeline: IndexingPipeline = Depends(get_pipeline),
    store: MilvusStore = Depends(get_store),
) -> UploadResponse:
    """通过文件上传 — multipart/form-data

    适用于前端直接上传文件。
    """
    import tempfile
    from pathlib import Path

    t0 = time.time()
    suffix = Path(file.filename or "upload").suffix
    content = await file.read()

    # 写入临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parse_result = parse_file(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not parse_result.markdown:
        return UploadResponse(
            status="failed",
            source_file=file.filename or "unknown",
            errors=parse_result.errors or ["解析结果为空"],
            elapsed_seconds=round(time.time() - t0, 1),
        )

    result = pipeline.run_from_text(
        text=parse_result.markdown,
        source_file=file.filename or "upload",
        doc_type=parse_result.document.doc_type,
        recreate_collection=recreate_collection,
    )

    return UploadResponse(
        status=result["status"],
        source_file=file.filename or "upload",
        total_chunks=result.get("total_chunks", 0),
        embedded=result.get("embedded", 0),
        inserted=result.get("inserted", 0),
        elapsed_seconds=result.get("elapsed_seconds", 0),
        errors=result.get("errors", []),
    )


@router.delete("/documents/{source_file:path}")
async def delete_document(
    source_file: str,
    store: MilvusStore = Depends(get_store),
) -> dict:
    """按来源文件名删除文档的所有 chunk"""
    deleted = store.delete_by_source(source_file)
    return {"deleted": deleted, "source_file": source_file}
