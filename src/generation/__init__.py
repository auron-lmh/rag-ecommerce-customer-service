"""模块6: 幻觉检测 + 自纠正闭环 — G-Eval自检 / 改写重搜 / 兜底降级

使用:
    from src.generation import get_corrector
    corrector = get_corrector()
    result = corrector.generate_with_correction("怎么退货？")
    print(result.answer)
    print(result.was_corrected)
    print(result.correction_rounds)
"""

from .hallucination_detector import HallucinationDetector, get_detector
from .models import Claim, ClaimVerdict, GenerationResult, HallucinationCheck
from .self_correction import SelfCorrector, get_corrector

__all__ = [
    "Claim",
    "ClaimVerdict",
    "GenerationResult",
    "HallucinationCheck",
    "HallucinationDetector",
    "get_detector",
    "SelfCorrector",
    "get_corrector",
]
