"""模块3 端到端流水线 — CleanedDocument/Chunk → Embed → Milvus

串联模块1-3: 清洗后的文档 → 分块 → 向量化 → 入库
"""

import logging
import time
from typing import Optional

from src.chunking.models import Chunk, ChunkResult
from src.chunking.router import chunk_document
from src.config import settings
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
        doc_metadata: dict | None = None,
    ) -> dict:
        """Chunk → Embed → Milvus

        Args:
            chunk_result: 模块2的分块结果
            recreate_collection: 是否重建 collection（⚠️ 会删除全部数据）
            doc_metadata: 文档级元数据（版本号/生效时间/过期时间等，改进4），
                          合并进每个 chunk 的 metadata

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

        # 切分策略变更检测（混用不同 chunk 策略/尺寸会导致检索不一致）
        self._check_chunk_strategy_mismatch(chunk_result)

        logger.info("开始入库: %s, %d chunks", chunk_result.source_file, len(chunks))

        # ── 改进5: 增量更新——同 source 先删旧数据，避免重复向量 ──
        # 只替换该文件，不动其他文档（相比 recreate_collection 全量重建，成本低）
        if not recreate_collection:
            try:
                deleted = self.store.delete_by_source(chunk_result.source_file)
                if deleted:
                    logger.info(
                        "增量更新: 删除 %d 条旧数据 (%s)",
                        deleted,
                        chunk_result.source_file,
                    )
            except Exception as e:
                logger.warning("增量更新删除旧数据失败（继续插入）: %s", e)

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

        # 改进5: 内容哈希——识别文件是否变化（增量更新的判断依据）
        import hashlib

        content_hash = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16]

        # 入库时间戳（政策更新/追溯用）——同一批次所有 chunk 一致
        from datetime import datetime

        ingested_at = datetime.now().isoformat(timespec="seconds")

        metadata_list = [
            {
                "doc_type": chunk_result.doc_type.value,
                "source_file": chunk_result.source_file,
                "page_number": c.page_number,
                "heading_path": c.heading_path,
                "section_title": c.section_title,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
                "strategy": c.strategy.value,
                "target_size": c.target_size,  # 切分目标尺寸（检测"切分策略变更"）
                "char_count": c.char_count,
                "token_count": c.token_count,
                # 修复: 记录 embedding 模型+维度，用于校验"索引与查询同模型"硬规则
                "embedding_model": self.embedder.model_name,
                "embedding_dim": self.embedder.dimension,
                # 新增: 入库时间戳——配合 version/effective 窗口做政策更新追溯
                "ingested_at": ingested_at,
            }
            for c in chunks
        ]

        # 改进4: 合并入库方提供的文档级元数据（version/effective_from/effective_to）
        if doc_metadata:
            for meta in metadata_list:
                for k, v in doc_metadata.items():
                    if v is not None:
                        meta[k] = v

        for meta in metadata_list:
            meta["content_hash"] = content_hash

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

        # ── 实时性闭环（改进）: 知识更新成功后主动失效检索缓存 ──
        # 行业核心: 缓存失效必须绑定源数据变更事件。
        # 若不失效，政策更新后用户在缓存 TTL（1h）内仍拿到旧答案。
        # 只清 query 层缓存，保留 embedding/LLM 缓存。
        if inserted > 0:
            try:
                from src.engineering import get_cache

                cleared = get_cache().clear_query_cache()
                if cleared:
                    logger.info("知识已更新，失效 %d 条检索缓存", cleared)
            except Exception as e:
                logger.warning("检索缓存失效失败: %s", e)

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

    # ── 切分策略变更检测 ──

    def _check_chunk_strategy_mismatch(self, chunk_result: ChunkResult) -> None:
        """检测切分策略变更——库中已有 chunk 的策略/尺寸与新批次不一致则告警

        行业规则（阿里云/CSDN 入库最佳实践）: 切分策略变更必须全量重建。
        场景: 库用 target_size=1000 入了一批，后来源码改 target_size=50 只重传部分文件，
        同一库混入两种粒度的 chunk → 检索不一致。此检测在入库时发现并告警。
        """
        try:
            if not self.store.collection_exists() or not chunk_result.chunks:
                return

            current_strategy = chunk_result.strategy.value
            current_target = chunk_result.chunks[0].target_size

            # 采样库中已有 chunk 的元数据
            res = self.store.client.query(
                collection_name=settings.milvus_collection,
                filter='doc_type != ""',
                output_fields=["chunk_metadata"],
                limit=50,
            )
            existing_targets = {
                m.get("chunk_metadata", {}).get("target_size", 0) for m in res
            }
            existing_strategies = {
                m.get("chunk_metadata", {}).get("strategy", "") for m in res
            }

            if existing_targets and current_target not in existing_targets:
                logger.warning(
                    "⚠️ 切分策略变更检测: 库中已有 target_size=%s，本次=%s。"
                    "混用不同切分策略会导致检索不一致，建议全量重建（recreate_collection=True）。",
                    sorted(existing_targets),
                    current_target,
                )
            if existing_strategies and current_strategy not in existing_strategies:
                logger.warning(
                    "⚠️ 切分策略变更检测: 库中已有 strategy=%s，本次=%s。建议全量重建。",
                    existing_strategies,
                    current_strategy,
                )
        except Exception as e:
            logger.debug("切分策略变更检测跳过（库为空或查询失败）: %s", e)

    # ── 便捷方法 ──

    def run_from_text(
        self,
        text: str,
        source_file: str,
        doc_type: DocType,
        recreate_collection: bool = False,
        doc_metadata: dict | None = None,
    ) -> dict:
        """从原始文本全流程: 分块 → 向量化 → 入库"""
        chunk_result = chunk_document(
            text,
            source_file=source_file,
            doc_type=doc_type,
        )
        return self.run(
            chunk_result,
            recreate_collection=recreate_collection,
            doc_metadata=doc_metadata,
        )

    def run_from_cleaned_docs(
        self,
        cleaned_docs: list[CleanedDocument],
        source_file: str,
        doc_type: DocType,
        recreate_collection: bool = False,
        doc_metadata: dict | None = None,
    ) -> dict:
        """从模块1的 CleanedDocument 全流程"""
        text = "\n\n".join(d.content for d in cleaned_docs)
        return self.run_from_text(
            text,
            source_file,
            doc_type,
            recreate_collection,
            doc_metadata=doc_metadata,
        )

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
