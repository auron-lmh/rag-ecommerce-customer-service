"""高敏承诺护栏 — 拦截"AI 瞎承诺政策/价格/退款"类幻觉

行业痛点（跨境卖家案例: AI 承诺"7天无理由"实际 15 天，亏损十几万）:
  主流模型在事实问答上幻觉率 10~30%，价格/退款/政策承诺是高危区。
  高敏内容要求更严的忠实度阈值（行业建议 85~95%），不达标强制转人工，
  杜绝"看起来很可信的瞎承诺"。

与自纠正/幻觉检测的关系:
  - hallucination_detector: 通用幻觉检测（G-Eval）
  - promise_guard: 专门识别"含钱/政策/承诺"的高敏回答，提高核验门槛
"""

import logging
import re

logger = logging.getLogger(__name__)

# 高敏内容更高门槛（普通内容 0.7，高敏内容 0.85）
HIGH_STAKE_FAITHFULNESS = 0.85

# 高敏承诺模式（命中即提高核验门槛）
_HIGH_STAKE_PATTERNS: dict[str, list[str]] = {
    "价格": [
        r"¥?\s*\d+(?:\.\d+)?\s*元",
        r"(价格|售价|多少钱|到手价|优惠价|原价|现价|补差价)",
    ],
    "退款赔偿": [
        r"(退款|退钱|赔偿|补偿|赔付|返现|全额退|退差额)",
        # 修复: "假一赔三"等不出现"赔偿"二字的承诺
        r"(假一赔|赔\s*\d+\s*倍|等值赔偿|\d+\s*倍赔)",
    ],
    "政策承诺": [
        r"(保修|包退|包换|无理由|退货期|退货期限|承诺|保证|限时|秒杀|活动价|政策|规则)",
    ],
}

_COMPILED = {
    cat: [re.compile(p) for p in pats] for cat, pats in _HIGH_STAKE_PATTERNS.items()
}


def detect_high_stakes(text: str) -> list[str]:
    """检测文本是否含高敏承诺（价格/退款/政策承诺）

    Args:
        text: 生成的回答文本

    Returns:
        命中的高敏类别列表（空 = 无高敏内容）
    """
    if not text:
        return []
    hits = []
    for category, patterns in _COMPILED.items():
        for p in patterns:
            if p.search(text):
                hits.append(category)
                break
    return hits


def needs_human_review(answer: str, faithfulness: float) -> tuple[bool, list[str]]:
    """判断高敏内容是否需人工核验

    Args:
        answer: 生成的回答
        faithfulness: 忠实度分数（0~1）

    Returns:
        (是否需人工, 命中的高敏类别)
    """
    cats = detect_high_stakes(answer)
    if not cats:
        return False, []
    need = faithfulness < HIGH_STAKE_FAITHFULNESS
    if need:
        logger.info(
            "高敏承诺需人工核验: %s, faithfulness=%.2f < %.2f",
            ",".join(cats),
            faithfulness,
            HIGH_STAKE_FAITHFULNESS,
        )
    return need, cats
