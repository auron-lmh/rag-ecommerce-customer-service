"""情绪识别 — 分级 + 驱动转人工/安抚

行业实践（融云/阿里云等）: 情绪分级必须驱动响应模式变化:
  - calm         → 标准流程
  - dissatisfied → 减少解释，优先给方案
  - angry        → 压缩提问轮次，angry + 退款/投诉争议 → 升级人工
  - extreme      → 直接升级人工（辱骂/威胁/起诉），不能让机器人继续"磨用户"

实现: 启发式关键词 + 语气符号打分（确定性、零成本、可测试）。
生产可替换为 BERT/LLM 情绪分类（保留 confidence 字段，低置信度退回 calm）。
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EmotionLevel(str, Enum):
    """情绪分级"""

    CALM = "calm"  # 平静
    DISSATISFIED = "dissatisfied"  # 不满
    ANGRY = "angry"  # 愤怒
    EXTREME = "extreme"  # 极端（辱骂/威胁/法律升级）


@dataclass
class EmotionResult:
    """情绪识别结果"""

    level: EmotionLevel
    confidence: float  # 0~1
    reason: str = ""


# ── 分级关键词 ──

_EXTREME_KEYWORDS = [
    "垃圾",
    "骗子",
    "黑店",
    "滚",
    "妈的",
    "贱",
    "找死",
    "欠骂",
    "起诉",
    "告你",
    "法院",
    "律师",
    "曝光",
    "媒体",
    "12315",
    "工商",
    "投诉到底",
    "赔钱",
    "赔偿损失",
    "假货",
]

_ANGRY_KEYWORDS = [
    "气死",
    "过分",
    "凭什么",
    "服了",
    "搞什么",
    "烦死",
    "太坑",
    "坑人",
    "什么玩意儿",
    "真是够了",
    "忍不了",
    "生气",
    "恼火",
]

_DISSATISFIED_KEYWORDS = [
    "太慢",
    "很差",
    "糟糕",
    "失望",
    "不满意",
    "还没到",
    "等了好久",
    "不靠谱",
    "差评",
    "体验差",
    "问题很多",
]


class EmotionDetector:
    """情绪识别器 — 启发式分级

    使用方式:
        detector = EmotionDetector()
        result = detector.detect("你们什么垃圾公司，我要投诉！")
        print(result.level)  # EmotionLevel.EXTREME
    """

    def detect(self, text: str, history: list[dict] | None = None) -> EmotionResult:
        """检测情绪等级

        Args:
            text: 用户当前输入
            history: 对话历史 [{"role": "...", "content": "..."}]（可选）

        Returns:
            EmotionResult
        """
        if not text:
            return EmotionResult(level=EmotionLevel.CALM, confidence=0.0)

        # ── 极端（辱骂/威胁/法律）──
        extreme_hits = [kw for kw in _EXTREME_KEYWORDS if kw in text]
        if extreme_hits:
            return EmotionResult(
                level=EmotionLevel.EXTREME,
                confidence=min(0.95, 0.7 + 0.15 * len(extreme_hits)),
                reason=f"极端情绪词: {', '.join(extreme_hits[:3])}",
            )

        # ── 愤怒（愤怒词 + 感叹号爆发）──
        angry_hits = [kw for kw in _ANGRY_KEYWORDS if kw in text]
        exclamations = text.count("！") + text.count("!")
        if angry_hits or exclamations >= 2:
            return EmotionResult(
                level=EmotionLevel.ANGRY,
                confidence=min(0.85, 0.6 + 0.1 * len(angry_hits) + 0.05 * exclamations),
                reason=(f"愤怒词: {', '.join(angry_hits[:3])}, 感叹号x{exclamations}"),
            )

        # ── 不满 ──
        dissatisfied_hits = [kw for kw in _DISSATISFIED_KEYWORDS if kw in text]
        if dissatisfied_hits:
            return EmotionResult(
                level=EmotionLevel.DISSATISFIED,
                confidence=min(0.7, 0.5 + 0.1 * len(dissatisfied_hits)),
                reason=f"不满词: {', '.join(dissatisfied_hits[:3])}",
            )

        return EmotionResult(level=EmotionLevel.CALM, confidence=0.3)


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_emotion_detector() -> EmotionDetector:
    """获取情绪识别器单例"""
    return EmotionDetector()
