"""统一配置中心 — 所有模块从这里读取配置"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """应用配置，自动从 .env / 环境变量读取"""

    # ========== 阿里云百炼 ==========
    bailian_api_key: str = os.getenv("BAILIAN_API_KEY", "")
    bailian_base_url: str = os.getenv(
        "BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    bailian_doc_parse_url: str = os.getenv(
        "BAILIAN_DOC_PARSE_URL",
        "https://dashscope.aliyuncs.com/api/v1/services/fileparser/parse",
    )

    # ========== 智谱 GLM ==========
    zhipu_api_key: str = os.getenv("ZHIPU_API_KEY", "")
    zhipu_base_url: str = os.getenv(
        "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
    )

    # ========== DeepSeek ==========
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )

    # ========== OpenAI 兼容 ==========
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # ========== LLM 主/备模型 ==========
    default_model: str = "deepseek-chat"
    fallback_model: str = "qwen-plus"
    vision_model: str = "glm-4v-flash"  # 图片理解（性价比高）
    ocr_model: str = "qwen-vl-ocr-latest"  # 文档OCR

    # ========== 文档解析 ==========
    pdf_max_pages: int = 50  # PDF单次最大解析页数
    pdf_ocr_enabled: bool = True  # 扫描件自动OCR
    doc_parse_timeout: int = 120  # 文档解析超时(秒)

    # ========== Embedding ==========
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_device: str = "cpu"

    # ========== Milvus ==========
    milvus_host: str = os.getenv("MILVUS_HOST", "127.0.0.1")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    milvus_collection: str = "ecommerce_knowledge"

    # ========== Redis ==========
    redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
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
