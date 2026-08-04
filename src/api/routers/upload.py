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

    # ── 路径安全检查: 限制文件必须在 data_dir 范围内 ──
    from pathlib import Path

    from src.config import settings

    resolved = Path(req.file_path).resolve()
    allowed_base = settings.data_dir.resolve()
    if not str(resolved).startswith(str(allowed_base)):
        raise HTTPException(
            status_code=403,
            detail="文件路径超出允许范围，仅支持 data/ 目录下的文件",
        )

    try:
        parse_result = parse_file(str(resolved))
    except Exception as e:
        logger.exception("文件解析失败: %s", req.file_path)
        raise HTTPException(status_code=400, detail="文件解析失败")

    if not parse_result.markdown:
        return UploadResponse(
            status="failed",
            source_file=req.file_path,
            errors=parse_result.errors or ["解析结果为空"],
            elapsed_seconds=round(time.time() - t0, 1),
        )

    # 政策时效元数据（改进4）
    doc_metadata = {
        "version": req.version,
        "effective_from": req.effective_from,
        "effective_to": req.effective_to,
    }

    result = pipeline.run_from_text(
        text=parse_result.markdown,
        source_file=req.file_path,
        doc_type=parse_result.document.doc_type,
        recreate_collection=req.recreate_collection,
        doc_metadata=doc_metadata,
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
    version: str | None = Form(None),
    effective_from: str | None = Form(None),
    effective_to: str | None = Form(None),
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

    # 政策时效元数据（改进4）
    doc_metadata = {
        "version": version,
        "effective_from": effective_from,
        "effective_to": effective_to,
    }

    # 修复 (P0): source_file 用"内容哈希_文件名"唯一化，避免同名文档互相删向量
    import hashlib

    filename = file.filename or "upload"
    content_hash = hashlib.sha256(content).hexdigest()[:12]
    unique_source = f"{content_hash}_{filename}"

    result = pipeline.run_from_text(
        text=parse_result.markdown,
        source_file=unique_source,
        doc_type=parse_result.document.doc_type,
        recreate_collection=recreate_collection,
        doc_metadata=doc_metadata,
    )

    return UploadResponse(
        status=result["status"],
        source_file=unique_source,
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
