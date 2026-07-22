"""模块6 数据模型 — 生成与幻觉检测"""

from dataclasses import dataclass, field
from enum import Enum


class ClaimVerdict(str, Enum):
    """事实断言判定结果"""

    SUPPORTED = "supported"  # 有依据
    PARTIALLY = "partially"  # 部分有依据
    HALLUCINATION = "hallucination"  # 无依据（幻觉）


@dataclass
class Claim:
    """单条事实断言"""

    text: str
    verdict: ClaimVerdict
    evidence: str = ""  # 来源片段（supported/partially 时）
    reason: str = ""  # 判定理由（hallucination 时）


@dataclass
class HallucinationCheck:
    """幻觉检测结果"""

    claims: list[Claim]
    overall_faithfulness: float  # 0~1, 整体忠实度
    has_hallucination: bool
    hallucination_count: int = 0
    supported_count: int = 0
    partial_count: int = 0


@dataclass
class GenerationResult:
    """生成结果"""

    answer: str
    sources: list[str]  # 引用来源
    faithfulness: float  # 忠实度分数
    hallucination_check: HallucinationCheck | None = None
    correction_rounds: int = 0  # 自纠正轮数
    was_corrected: bool = False  # 是否经过纠正
    final_level: int = 1  # 最终降级级别
