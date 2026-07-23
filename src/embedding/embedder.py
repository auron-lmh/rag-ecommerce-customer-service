"""Qwen3-VL-Embedding 向量化器 — DashScope 多模态 API

特性:
  - 2048-dim 向量 (可调 256~2560)
  - 文本 + 图片同一向量空间 (以文搜图、以图搜图)
  - 固定窗口速率限制 (120 RPM)
  - 429 指数退避重试 (最多 5 次)
  - 单次请求最多 20 个 content，其中图片 ≤ 5

API: dashscope.MultiModalEmbedding.call() (非 OpenAI 兼容协议)
参考: PythonProject1 RAG 项目 utils/embeddings_utils.py
"""

import logging
import time
from functools import lru_cache
from typing import Optional

import dashscope
import numpy as np

from src.config import settings

from .models import BatchEmbeddingResult, EmbeddingResult

logger = logging.getLogger(__name__)

# 查询文本的前缀指令 (提升检索质量)
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages:"

# API 限流与重试参数
RPM_LIMIT = 120
WINDOW_SECONDS = 60
MAX_429_RETRIES = 5
BASE_BACKOFF = 2.0
MAX_ITEMS_PER_CALL = 20  # 单次 API 最多 20 个 content
MAX_IMAGES_PER_CALL = 5  # 单次 API 最多 5 张图片


# ═══════════════════════════════════════
# 速率限制器
# ═══════════════════════════════════════


class _RateLimiter:
    """固定窗口速率限制器（线程安全）"""

    def __init__(self, limit: int = RPM_LIMIT, window_seconds: int = WINDOW_SECONDS):
        self.limit = limit
        self.window_seconds = window_seconds
        self.window_start = time.monotonic()
        self.count = 0
        self._lock = __import__("threading").Lock()  # 线程安全锁

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.window_start
            if elapsed >= self.window_seconds:
                self.window_start = now
                self.count = 0
            if self.count >= self.limit:
                sleep_sec = self.window_seconds - elapsed
                if sleep_sec > 0:
                    logger.debug("速率限制: 等待 %.2fs", sleep_sec)
                    time.sleep(sleep_sec)
                self.window_start = time.monotonic()
                self.count = 0
            self.count += 1


# ═══════════════════════════════════════
# Embedder
# ═══════════════════════════════════════


class Embedder:
    """Qwen3-VL-Embedding 向量化封装 (DashScope API)

    使用方式:
        embedder = Embedder()
        result = embedder.embed_chunks(chunks)       # 批量文本
        vec = embedder.embed_query("怎么退货?")       # 查询向量
        vec = embedder.embed_image("page_1.jpg")      # 图片向量
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        dimension: Optional[int] = None,
        batch_size: int = MAX_ITEMS_PER_CALL,
    ):
        self.model_name = model_name or settings.embedding_model
        self._api_key = api_key or settings.bailian_api_key
        self._dimension = dimension or settings.embedding_dim
        self.batch_size = min(batch_size, MAX_ITEMS_PER_CALL)
        self._limiter = _RateLimiter(limit=settings.embedding_rpm)

    # ── 维度 ──

    @property
    def dimension(self) -> int:
        return self._dimension

    # ── 文本批量向量化 ──

    def embed_chunks(
        self,
        texts: list[str],
        chunk_ids: list[str],
        metadata_list: Optional[list[dict]] = None,
        show_progress: bool = True,
    ) -> BatchEmbeddingResult:
        """批量向量化 chunk 文本

        Args:
            texts: 文本列表
            chunk_ids: chunk_id 列表（一一对应）
            metadata_list: 元数据列表（一一对应，可选）
            show_progress: 是否显示进度

        Returns:
            BatchEmbeddingResult
        """
        t0 = time.time()
        n = len(texts)
        errors: list[str] = []

        if n == 0:
            return BatchEmbeddingResult(
                embeddings=[],
                total=0,
                dimension=self.dimension,
                model_name=self.model_name,
                elapsed_seconds=0,
            )

        if metadata_list is None:
            metadata_list = [{} for _ in range(n)]

        logger.info("开始向量化 %d 条文本 (API, batch_size=%d)", n, self.batch_size)

        all_vectors: list[list[float]] = []
        failed_indices: set[int] = set()  # 记录失败的批次索引
        total_batches = (n + self.batch_size - 1) // self.batch_size

        for batch_idx in range(0, n, self.batch_size):
            batch_texts = texts[batch_idx : batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1

            if show_progress:
                print(
                    f"\r[Embedding] {batch_num}/{total_batches} "
                    f"({min(batch_idx + self.batch_size, n)}/{n})",
                    end="",
                    flush=True,
                )

            try:
                batch_vectors = self._call_api(batch_texts)
                all_vectors.extend(batch_vectors)
            except Exception as e:
                logger.error("批次 %d 向量化失败: %s", batch_num, e)
                errors.append(f"batch[{batch_idx}:{batch_idx + len(batch_texts)}]: {e}")
                # 关键修复: 记录失败索引，不填充零向量（避免污染检索）
                for j in range(len(batch_texts)):
                    failed_indices.add(batch_idx + j)
                # 填充占位向量（后续会被过滤）
                all_vectors.extend([[0.0] * self.dimension for _ in batch_texts])

        if show_progress:
            print()  # 换行

        # 组装结果（过滤失败的向量）
        embeddings: list[EmbeddingResult] = []
        skipped_count = 0
        for i in range(n):
            if i in failed_indices:
                skipped_count += 1
                continue  # 跳过失败的向量，不写入 Milvus
            embeddings.append(
                EmbeddingResult(
                    chunk_id=chunk_ids[i],
                    vector=(
                        all_vectors[i]
                        if i < len(all_vectors)
                        else [0.0] * self.dimension
                    ),
                    text=texts[i],
                    metadata=metadata_list[i] if i < len(metadata_list) else {},
                )
            )

        if skipped_count > 0:
            logger.warning("跳过 %d 个失败的向量（避免零向量污染检索）", skipped_count)

        elapsed = time.time() - t0
        logger.info(
            "向量化完成: %d 条, %d-dim, 耗时 %.1fs, 速度 %.0f 条/秒, 错误 %d",
            n,
            self.dimension,
            elapsed,
            n / max(elapsed, 0.001),
            len(errors),
        )

        return BatchEmbeddingResult(
            embeddings=embeddings,
            total=n,
            dimension=self.dimension,
            model_name=self.model_name,
            elapsed_seconds=round(elapsed, 2),
            errors=errors,
        )

    # ── 查询向量化 ──

    def embed_query(self, query: str) -> np.ndarray:
        """查询文本 → 向量 (带 instruction prefix, L2 归一化)"""
        prefixed = f"{QUERY_INSTRUCTION} {query}"
        vec = self._call_api([prefixed])[0]
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def embed_queries(self, queries: list[str]) -> np.ndarray:
        """批量查询向量化 (L2 归一化)"""
        prefixed = [f"{QUERY_INSTRUCTION} {q}" for q in queries]
        all_vecs = []
        for batch_idx in range(0, len(prefixed), self.batch_size):
            batch = prefixed[batch_idx : batch_idx + self.batch_size]
            all_vecs.extend(self._call_api(batch))
        arr = np.array(all_vecs, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return arr / norms

    # ── 图片向量化 ──

    def embed_image(self, image_path: str) -> np.ndarray:
        """图片 → 向量 (与文本在同一向量空间, L2 归一化)

        Args:
            image_path: 本地图片路径或 URL
        """
        import base64
        import mimetypes

        if image_path.startswith(("http://", "https://")):
            image_input = image_path
        else:
            mime = mimetypes.guess_type(image_path)[0] or "image/png"
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            image_input = f"data:{mime};base64,{b64}"

        vec = self._call_api([{"image": image_input}])[0]
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    def embed_image_base64(
        self, image_b64: str, mime_type: str = "image/jpeg"
    ) -> np.ndarray:
        """base64 图片 → 向量 (L2 归一化)"""
        data_uri = f"data:{mime_type};base64,{image_b64}"
        vec = self._call_api([{"image": data_uri}])[0]
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr

    # ── 核心 API 调用 ──

    def _call_api(self, contents: list) -> list[list[float]]:
        """调用 DashScope MultiModalEmbedding API，带限流+重试

        Args:
            contents: 文本字符串列表 或 dict 列表 [{"text": "..."}, {"image": "..."}]

        Returns:
            向量列表 list[list[float]]
        """
        # 统一转为 dict 格式
        inputs = []
        for c in contents:
            if isinstance(c, str):
                inputs.append({"text": c})
            elif isinstance(c, dict):
                inputs.append(c)
            else:
                raise TypeError(f"不支持的 content 类型: {type(c)}")

        if not inputs:
            return []

        # 检查图片数量限制
        img_count = sum(1 for item in inputs if "image" in item)
        if img_count > MAX_IMAGES_PER_CALL:
            raise ValueError(
                f"单次 API 调用最多 {MAX_IMAGES_PER_CALL} 张图片，当前 {img_count} 张"
            )

        # 带重试的 API 调用
        last_error = None
        for attempt in range(MAX_429_RETRIES + 1):
            self._limiter.acquire()

            try:
                response = dashscope.MultiModalEmbedding.call(
                    model=self.model_name,
                    input=inputs,
                    api_key=self._api_key,
                    dimension=self._dimension,
                )
            except Exception as e:
                logger.error("DashScope API 异常 (attempt %d): %s", attempt + 1, e)
                last_error = e
                if attempt < MAX_429_RETRIES:
                    wait = BASE_BACKOFF**attempt
                    time.sleep(wait)
                continue

            status = getattr(response, "status_code", None)

            if status == 200:
                try:
                    embeddings = response.output["embeddings"]
                    return [e["embedding"] for e in embeddings]
                except (KeyError, IndexError, TypeError) as e:
                    logger.error("解析 embedding 响应失败: %s", e)
                    raise RuntimeError(f"解析 embedding 响应失败: {e}") from e

            # 429 Too Many Requests → 指数退避
            if status == 429:
                retry_after = None
                try:
                    headers = getattr(response, "headers", {}) or {}
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra:
                        retry_after = float(ra)
                except Exception:
                    pass
                wait = retry_after or (BASE_BACKOFF**attempt)
                logger.warning(
                    "429 限流 (attempt %d/%d), 等待 %.1fs",
                    attempt + 1,
                    MAX_429_RETRIES,
                    wait,
                )
                if attempt < MAX_429_RETRIES:
                    time.sleep(wait)
                last_error = RuntimeError(
                    f"429 Too Many Requests: {getattr(response, 'message', '')}"
                )
                continue

            # 其他错误
            code = getattr(response, "code", "")
            msg = getattr(response, "message", "")
            raise RuntimeError(
                f"DashScope API 错误: status={status}, code={code}, message={msg}"
            )

        raise last_error or RuntimeError("DashScope API 调用失败: 未知错误")

    # ── 资源释放 (API 模式无本地模型，no-op) ──

    def unload(self):
        """API 模式无需释放资源"""
        pass


# ═══════════════════════════════════════
# 模块级单例
# ═══════════════════════════════════════

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_embedder() -> Embedder:
    return Embedder()
