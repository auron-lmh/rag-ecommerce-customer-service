"""统一配置中心 — 所有模块从这里读取配置

pydantic-settings 自动从以下来源加载（优先级从高到低）：
  1. 环境变量 (export BAILIAN_API_KEY=...)
  2. .env 文件
  3. 类定义的默认值

因此字段默认值应设为空字符串或合理默认值，
NOT os.getenv() —— 后者在类定义时求值，此时 .env 尚未加载。

模型方案 (2026-07):
  PDF 解析:   qwen3.7-plus (替代已下线的 qwen-vl-max)
  Embedding:  qwen3-vl-embedding → 2048-dim (文本+图片同一向量空间)
  全文检索:   BM25 + Dense (WeightedRanker)
  Reranker:   qwen3-vl-rerank (可选)
"""

from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """应用配置，自动从 .env / 环境变量读取"""

    # ========== 阿里云百炼 / DashScope ==========
    bailian_api_key: str = ""
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_doc_parse_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/fileparser/parse"
    )
    # DashScope 专有 API 端点（Embedding / Reranker 不走 OpenAI 兼容协议）
    dashscope_embedding_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/embeddings"
        "/multimodal-embedding/multimodal-embedding"
    )
    dashscope_rerank_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/rerank"
        "/text-rerank/text-rerank"
    )

    # ========== 智谱 GLM ==========
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    # ========== DeepSeek ==========
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # ========== OpenAI 兼容 ==========
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # ========== LLM 主/备模型 ==========
    default_model: str = "deepseek-chat"
    fallback_model: str = "qwen-plus"
    vision_model: str = "qwen3.7-plus"  # 图片理解（替代已下线 glm-4v-flash）
    ocr_model: str = "qwen3.7-plus"  # PDF OCR（替代已下线 qwen-vl-max）

    # ========== 文档解析 ==========
    pdf_max_pages: int = 50  # PDF单次最大解析页数
    pdf_ocr_enabled: bool = True  # 扫描件自动OCR
    doc_parse_timeout: int = 120  # 文档解析超时(秒)

    # ========== Embedding (DashScope 多模态) ==========
    embedding_model: str = "qwen3-vl-embedding"
    embedding_dim: int = 2048  # qwen3-vl-embedding 支持 256~2560
    embedding_rpm: int = 120  # DashScope Embedding API 限流 (RPM)

    # ========== Reranker (DashScope) ==========
    reranker_model: str = "qwen3-vl-rerank"
    reranker_enabled: bool = True  # 是否启用重排序
    reranker_top_n: int = 5  # 重排序后返回数

    # ========== Milvus ==========
    milvus_host: str = "192.168.191.128"
    milvus_port: int = 19530
    milvus_user: str = "root"
    milvus_password: str = "Milvus"
    milvus_collection: str = "ecommerce_knowledge"
    milvus_dim: int = 2048  # qwen3-vl-embedding 输出维度

    # ========== Redis ==========
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    # ========== 检索参数 ==========
    retrieval_top_k: int = 5
    retrieval_dense_top_k: int = 20
    retrieval_sparse_top_k: int = 20
    retrieval_similarity_threshold: float = 0.7

    # ========== 幻觉检测 ==========
    max_correction_rounds: int = 2
    faithfulness_threshold: float = 0.8

    # ========== 缓存 ==========
    query_cache_ttl: int = 3600
    embedding_cache_enabled: bool = True

    # ========== 服务 ==========
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ========== 路径 ==========
    data_dir: Path = PROJECT_ROOT / "data"
    raw_data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_data_dir: Path = PROJECT_ROOT / "data" / "processed"
    faq_dir: Path = PROJECT_ROOT / "data" / "faq"
    log_dir: Path = PROJECT_ROOT / "logs"
    model_dir: Path = PROJECT_ROOT / "models"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
