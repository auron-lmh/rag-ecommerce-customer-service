"""模块6.5 人工介入机制 — 高风险操作需要人工确认

场景:
  - 退款操作 → 需要人工确认
  - 投诉处理 → 需要人工介入
  - 敏感话题 → 需要人工审核

使用:
    handler = HumanInLoopHandler()
    result = handler.check_needs_human(query, intent, answer)
    if result["needs_human"]:
        # 转人工
        pass
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 需要人工介入的场景
HUMAN_REQUIRED_SCENARIOS = {
    "refund_request": {
        "description": "退款请求",
        "keywords": ["退款", "退钱", "退款到账", "退款失败"],
        "reason": "涉及资金操作，需要人工确认",
    },
    "complaint": {
        "description": "投诉",
        "keywords": ["投诉", "举报", "不满", "差评", "曝光"],
        "reason": "投诉需要人工跟进处理",
    },
    "sensitive_topic": {
        "description": "敏感话题",
        "keywords": ["法律", "律师", "起诉", "法院", "工商", "12315"],
        "reason": "涉及法律问题，需要人工介入",
    },
    "high_value_order": {
        "description": "高价值订单",
        "keywords": ["大额", "批量", "企业采购", "团购"],
        "reason": "大额订单需要人工跟进",
    },
}

# 需要人工审核的回答模式
ANSWER_REVIEW_PATTERNS = [
    "根据已有信息无法确认",
    "建议您咨询人工客服",
    "无法确认",
    "不确定",
]


class HumanInLoopHandler:
    """人工介入处理器

    使用方式:
        handler = HumanInLoopHandler()
        result = handler.check_needs_human(query, intent, answer)
    """

    def check_needs_human(
        self,
        query: str,
        intent: str = "",
        answer: str = "",
        confidence: Optional[float] = None,
        emotion: str = "calm",
    ) -> dict:
        """检查是否需要人工介入

        Args:
            query: 用户查询
            intent: 意图分类
            answer: 生成的回答
            confidence: 意图置信度
            emotion: 情绪等级（calm/dissatisfied/angry/extreme）

        Returns:
            {
                "needs_human": bool,
                "reason": str,
                "scenario": str,
                "priority": str,  # low / medium / high
            }
        """
        # 情绪极端 → 直接升级人工（辱骂/威胁/法律，不能让机器人继续"磨用户"）
        if emotion == "extreme":
            logger.info("人工介入: 情绪极端，直接升级")
            return {
                "needs_human": True,
                "reason": "用户情绪极端（辱骂/威胁/法律升级），需人工介入",
                "scenario": "high_emotion",
                "priority": "high",
            }

        # 愤怒 + 退款/投诉等高敏场景 → 升级人工（压缩提问轮次，避免激化）
        if emotion == "angry" and intent in (
            "return_refund",
            "complaint",
            "order_query",
        ):
            logger.info("人工介入: 愤怒 + 高敏意图 (%s)", intent)
            return {
                "needs_human": True,
                "reason": "用户情绪愤怒且涉及退款/投诉/订单，建议人工跟进",
                "scenario": "high_emotion",
                "priority": "high",
            }

        # 检查场景匹配
        for scenario_id, scenario in HUMAN_REQUIRED_SCENARIOS.items():
            for keyword in scenario["keywords"]:
                if keyword in query:
                    logger.info("人工介入: %s, 关键词: %s", scenario_id, keyword)
                    return {
                        "needs_human": True,
                        "reason": scenario["reason"],
                        "scenario": scenario_id,
                        "priority": self._get_priority(scenario_id),
                    }

        # 检查回答质量
        if answer:
            for pattern in ANSWER_REVIEW_PATTERNS:
                if pattern in answer:
                    logger.info("人工介入: 回答质量不足")
                    return {
                        "needs_human": True,
                        "reason": "系统回答不够确定，建议人工跟进",
                        "scenario": "low_confidence",
                        "priority": "low",
                    }

        # 检查意图置信度（仅当调用方明确提供了 confidence 才判断，防默认 0.0 误转人工）
        if confidence is not None and confidence < 0.4:
            logger.info("人工介入: 意图置信度过低 (%.2f)", confidence)
            return {
                "needs_human": True,
                "reason": "意图识别置信度过低，建议人工确认",
                "scenario": "low_confidence",
                "priority": "low",
            }

        return {
            "needs_human": False,
            "reason": "",
            "scenario": "",
            "priority": "",
        }

    def _get_priority(self, scenario_id: str) -> str:
        """获取优先级"""
        high_priority = [
            "refund_request",
            "complaint",
            "sensitive_topic",
            "high_emotion",
        ]
        medium_priority = ["high_value_order"]

        if scenario_id in high_priority:
            return "high"
        elif scenario_id in medium_priority:
            return "medium"
        return "low"

    def get_human_response_template(self, scenario: str) -> str:
        """获取人工介入的回复模板"""
        templates = {
            "refund_request": (
                "您的退款请求已收到。为了确保资金安全，"
                "我们将为您转接人工客服处理退款事宜。"
                "请稍候，客服人员将尽快与您联系。"
            ),
            "complaint": (
                "非常抱歉给您带来不好的体验。"
                "您的投诉我们非常重视，将为您转接专属客服处理。"
                "请稍候，我们会尽快为您解决问题。"
            ),
            "sensitive_topic": (
                "您的问题涉及相关法规政策，"
                "为了给您准确的解答，将为您转接专业客服。"
                "请稍候。"
            ),
            "high_value_order": (
                "您的订单需求已收到。"
                "大额订单我们将安排专属客服为您服务，"
                "请稍候，客服将尽快与您联系。"
            ),
            "low_confidence": (
                "您的问题我需要进一步确认，"
                "将为您转接人工客服获取更准确的信息。"
                "请稍候。"
            ),
            "high_emotion": (
                "非常抱歉给您带来不好的体验，让您着急了。"
                "我已经将您的情况优先记录，正在为您转接专属客服专员处理，"
                "会尽快给您一个满意的解决方案，请您稍候。"
            ),
        }
        return templates.get(scenario, "正在为您转接人工客服，请稍候。")


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_human_handler() -> HumanInLoopHandler:
    return HumanInLoopHandler()
