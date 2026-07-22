"""模块4 数据模型 — 意图分类与路由结果"""

from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    """6 类用户意图"""

    RETURN_REFUND = "return_refund"  # 退货退款
    PRODUCT_CONSULT = "product_consult"  # 商品咨询
    LOGISTICS = "logistics"  # 物流查询
    ORDER_QUERY = "order_query"  # 订单查询
    COMPLAINT = "complaint"  # 投诉建议
    CHITCHAT = "chitchat"  # 闲聊/其他


class RouteTarget(str, Enum):
    """路由目标"""

    RAG = "rag"  # 向量检索 + LLM 生成
    SQL = "sql"  # 结构化查询（预留）
    HYBRID = "hybrid"  # RAG + SQL
    DIRECT = "direct"  # 直接回复（闲聊）
    HUMAN = "human"  # 转人工


@dataclass
class IntentResult:
    """意图分类结果"""

    intent: Intent
    confidence: float  # 0~1
    reasoning: str = ""  # LLM 的判断理由
    entities: dict = field(default_factory=dict)  # 提取的实体（订单号、商品名等）


@dataclass
class RouteResult:
    """路由结果"""

    intent_result: IntentResult
    target: RouteTarget
    query: str  # 原始用户输入
    rewritten_query: str = ""  # 改写后的检索 query（RAG 路由用）
    handler: str = ""  # 处理器名称
