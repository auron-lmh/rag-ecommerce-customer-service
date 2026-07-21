"""模块3 端到端流水线 — CleanedDocument/Chunk → Embed → Milvus

串联模块1-3: 清洗后的文档 → 分块 → 向量化 → 入库
"""

import logging
import time
from typing import Optional

from src.chunking.models import Chunk, ChunkResult
from src.chunking.router import chunk_document
from src.ingestion.models import CleanedDocument, DocType

from .embedder import Embedder, get_embedder
from .milvus_store import MilvusStore

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """向量化入库流水线

    使用方式:
        pipeline = IndexingPipeline()
        # 方式1: 从 ChunkResult 直接入库
        pipeline.run(chunk_result)
        # 方式2: 从清洗后文本全流程
        pipeline.run_from_text(markdown_text, "policy.pdf", DocType.PDF)
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        store: Optional[MilvusStore] = None,
    ):
        self.embedder = embedder or get_embedder()
        self.store = store or MilvusStore()

    # ── 主入口 ──

    def run(
        self,
        chunk_result: ChunkResult,
        recreate_collection: bool = False,
    ) -> dict:
        """Chunk → Embed → Milvus

        Args:
            chunk_result: 模块2的分块结果
            recreate_collection: 是否重建 collection（⚠️ 会删除全部数据）

        Returns:
            {
                "status": "ok" | "partial" | "failed",
                "total_chunks": 8,
                "embedded": 8,
                "inserted": 8,
                "elapsed_seconds": 2.5,
                "errors": [...]
            }
        """
        t0 = time.time()
        chunks = chunk_result.chunks

        if not chunks:
            return {
                "status": "failed",
                "error": "无 chunk 可入库",
                "elapsed_seconds": 0,
            }

        logger.info("开始入库: %s, %d chunks", chunk_result.source_file, len(chunks))

        # ── 步骤1: 准备 Milvus collection ──
        try:
            self.store.create_collection(drop_if_exists=recreate_collection)
        except Exception as e:
            return {
                "status": "failed",
                "error": f"Milvus collection 创建失败: {e}",
                "elapsed_seconds": time.time() - t0,
            }

        # ── 步骤2: 向量化 ──
        texts = [c.content for c in chunks]
        chunk_ids = [c.chunk_id for c in chunks]
        metadata_list = [
            {
                "doc_type": chunk_result.doc_type.value,
                "source_file": chunk_result.source_file,
                "heading_path": c.heading_path,
                "section_title": c.section_title,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
                "strategy": c.strategy.value,
                "char_count": c.char_count,
                "token_count": c.token_count,
            }
            for c in chunks
        ]

        batch_result = self.embedder.embed_chunks(
            texts=texts,
            chunk_ids=chunk_ids,
            metadata_list=metadata_list,
            show_progress=True,
        )

        if batch_result.errors:
            logger.warning("向量化有 %d 个错误", len(batch_result.errors))

        # ── 步骤3: 写入 Milvus ──
        try:
            inserted = self.store.insert(batch_result.embeddings)
        except Exception as e:
            return {
                "status": "partial",
                "total_chunks": len(chunks),
                "embedded": len(batch_result.embeddings),
                "inserted": 0,
                "elapsed_seconds": round(time.time() - t0, 1),
                "errors": [f"Milvus 写入失败: {e}"],
            }

        elapsed = round(time.time() - t0, 1)
        logger.info(
            "入库完成: %d/%d chunks, %.1fs",
            inserted,
            len(chunks),
            elapsed,
        )

        return {
            "status": "ok" if inserted == len(chunks) else "partial",
            "total_chunks": len(chunks),
            "embedded": len(batch_result.embeddings),
            "inserted": inserted,
            "elapsed_seconds": elapsed,
            "errors": batch_result.errors,
        }

    # ── 便捷方法 ──

    def run_from_text(
        self,
        text: str,
        source_file: str,
        doc_type: DocType,
        recreate_collection: bool = False,
    ) -> dict:
        """从原始文本全流程: 分块 → 向量化 → 入库"""
        chunk_result = chunk_document(
            text,
            source_file=source_file,
            doc_type=doc_type,
        )
        return self.run(chunk_result, recreate_collection=recreate_collection)

    def run_from_cleaned_docs(
        self,
        cleaned_docs: list[CleanedDocument],
        source_file: str,
        doc_type: DocType,
        recreate_collection: bool = False,
    ) -> dict:
        """从模块1的 CleanedDocument 全流程"""
        text = "\n\n".join(d.content for d in cleaned_docs)
        return self.run_from_text(text, source_file, doc_type, recreate_collection)

    # ── 批量索引 ──

    def batch_index(
        self,
        chunk_results: list[ChunkResult],
        recreate_collection: bool = False,
    ) -> list[dict]:
        """批量索引多个 ChunkResult"""
        reports = []
        for i, cr in enumerate(chunk_results):
            logger.info("[%d/%d] 索引: %s", i + 1, len(chunk_results), cr.source_file)
            report = self.run(cr, recreate_collection=(recreate_collection and i == 0))
            reports.append(report)
        return reports
