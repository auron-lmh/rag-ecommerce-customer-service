"""模块12 Pydantic 模型 — 请求/响应数据结构"""

from pydantic import BaseModel, Field

# ── 查询 ──


class QueryRequest(BaseModel):
    """检索请求"""

    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    top_k: int = Field(5, ge=1, le=50, description="返回结果数")
    use_reranker: bool = Field(True, description="是否启用 Reranker 重排序")
    use_hybrid: bool = Field(True, description="是否启用 Hybrid Search (BM25+稠密)")
    threshold: float | None = Field(None, ge=0, le=1, description="最低相似度阈值")
    filter_doc_type: str | None = Field(None, description="按文档类型过滤")
    filter_source: str | None = Field(None, description="按来源文件过滤")


class SearchResultItem(BaseModel):
    """单条检索结果"""

    chunk_id: str
    text: str
    score: float
    doc_type: str = ""
    source_file: str = ""
    heading_path: list[str] = []


class QueryResponse(BaseModel):
    """检索响应"""

    query: str
    results: list[SearchResultItem]
    total_found: int
    query_time_ms: float
    threshold: float


# ── 上传 ──


class UploadRequest(BaseModel):
    """文件上传请求（路径方式）"""

    file_path: str = Field(..., description="文件绝对路径或 URL")
    recreate_collection: bool = Field(
        False, description="是否重建 collection（⚠️ 清空数据）"
    )


class UploadResponse(BaseModel):
    """上传响应"""

    status: str  # ok / partial / failed
    source_file: str
    total_chunks: int = 0
    embedded: int = 0
    inserted: int = 0
    elapsed_seconds: float = 0
    errors: list[str] = []


# ── 统计 ──


class StatsResponse(BaseModel):
    """Collection 统计"""

    exists: bool
    collection_name: str = ""
    total_vectors: int = 0
    dimension: int = 0
    model_name: str = ""


class HealthResponse(BaseModel):
    """健康检查"""

    status: str  # ok / degraded / unhealthy
    milvus: str = "unknown"
    embedder: str = "unknown"
    reranker: str = "unknown"
    collection: dict = {}


# ── 对话 ──


class ChatRequest(BaseModel):
    """客服对话请求"""

    query: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    top_k: int = Field(5, ge=1, le=20, description="检索结果数")
    use_reranker: bool = Field(True, description="是否启用 Reranker")


class ChatResponse(BaseModel):
    """客服对话响应"""

    query: str
    intent: str
    confidence: float
    target: str
    rewritten_query: str
    reasoning: str
    results: list[SearchResultItem]
    reply: str
    search_time_ms: float = 0
    degradation_level: int = 1  # 1=直接命中, 2=改写命中, 3=联网搜索, 4=兜底
    degradation_method: str = "hybrid"  # hybrid / rewritten / web_search / fallback
    faithfulness: float = 0.0  # 忠实度分数 (0~1)
    correction_rounds: int = 0  # 自纠正轮数
    was_corrected: bool = False  # 是否经过纠正
    needs_human: bool = False  # 是否需要人工介入
    human_reason: str = ""  # 人工介入原因
    human_priority: str = ""  # 人工介入优先级 (low/medium/high)
