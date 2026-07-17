"""模块1 数据模型 — 摄入阶段的数据结构"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DocType(str, Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    IMAGE = "image"
    WEB = "web"
    FAQ_JSON = "faq_json"
    PLAIN_TEXT = "plain_text"


class ParseStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RawDocument:
    """原始文档"""

    file_path: str
    doc_type: DocType
    file_size_bytes: int = 0
    ingested_at: datetime = field(default_factory=datetime.now)
    title: str = ""
    source: str = ""
    category: str = ""  # product / policy / faq


@dataclass
class ParseResult:
    """一次解析操作的结果"""

    document: RawDocument
    status: ParseStatus
    markdown: str = ""  # ★ 统一Markdown输出
    elements: list[dict] = field(default_factory=list)  # 结构化元素
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 成本追踪
    api_calls: int = 0
    api_cost_estimate: float = 0.0  # 预估费用(元)
    parse_time_ms: float = 0.0

    # PDF专用
    total_pages: int = 0
    parsed_pages: int = 0
    is_scanned: bool = False  # 是否扫描件
    extracted_images: list = field(default_factory=list)  # ExtractedImage[]
    page_qualities: list = field(default_factory=list)  # PageQuality[]
    pdf_image_section: str = ""  # Markdown图片引用区域

    # 图片专用
    image_quality: object | None = None  # ImageQuality
    was_resized: bool = False  # 是否被智能缩放
    resize_info: dict = field(default_factory=dict)  # 缩放详情

    # 文件预检
    file_validation: object | None = None  # FileValidation


@dataclass
class CleanedDocument:
    """清洗后的文档块"""

    chunk_id: str
    content: str  # 清洗后的Markdown/纯文本
    char_count: int

    source_file: str
    doc_type: DocType
    section_title: Optional[str] = None
    heading_path: list[str] = field(default_factory=list)

    removed_noise: list[str] = field(default_factory=list)
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None

    metadata: dict = field(default_factory=dict)
