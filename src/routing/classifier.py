"""模块4 意图分类器 — LLM Function Calling

使用 DeepSeek / Qwen 的 Function Calling 能力，将用户输入分类为 6 类意图。
"""

import json
import logging
from typing import Optional

import requests

from src.config import settings

from .models import Intent, IntentResult

logger = logging.getLogger(__name__)

# ── Function Calling 工具定义 ──

INTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_intent",
        "description": "将用户消息分类为电商客服意图，并提取关键实体",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [i.value for i in Intent],
                    "description": (
                        "用户意图类别:\n"
                        "- return_refund: 退货、退款、换货、售后\n"
                        "- product_consult: 商品参数、规格、使用方法、推荐\n"
                        "- logistics: 快递、配送、运费、发货时间\n"
                        "- order_query: 订单状态、支付、发票、订单修改\n"
                        "- complaint: 投诉、不满、建议、表扬\n"
                        "- chitchat: 问候、闲聊、超出电商范围的问题"
                    ),
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "分类置信度",
                },
                "reasoning": {
                    "type": "string",
                    "description": "一句话说明分类理由",
                },
                "entities": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "订单号（如有）",
                        },
                        "product_name": {
                            "type": "string",
                            "description": "商品名称（如有）",
                        },
                        "tracking_number": {
                            "type": "string",
                            "description": "快递单号（如有）",
                        },
                    },
                },
            },
            "required": ["intent", "confidence"],
        },
    },
}

SYSTEM_PROMPT = """你是一个电商客服意图分类器。

根据用户消息，判断其意图类别并提取关键实体。

意图分类规则:
1. return_refund — 涉及退货、退款、换货、质量问题是售后问题
2. product_consult — 咨询商品功能、参数、对比、推荐
3. logistics — 查询物流状态、配送时间、运费
4. order_query — 查询订单状态、支付问题、开发票
5. complaint — 表达不满、投诉、建议
6. chitchat — 问候、闲聊、或完全超出电商范围的问题

注意:
- 如果用户同时提到多个意图，选最核心的那个
- 如果不确定，选 confidence 最低的那个
- 提取所有可识别的实体（订单号、商品名、快递单号等）"""


class IntentClassifier:
    """LLM Function Calling 意图分类器

    使用方式:
        classifier = IntentClassifier()
        result = classifier.classify("我想退货，订单号是 12345")
        print(result.intent)  # Intent.RETURN_REFUND
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.default_model  # deepseek-chat
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url

    def classify(self, user_message: str) -> IntentResult:
        """分类用户意图

        Args:
            user_message: 用户输入文本

        Returns:
            IntentResult
        """
        try:
            return self._call_llm(user_message)
        except Exception as e:
            logger.error("意图分类失败，降级为关键词匹配: %s", e)
            return self._fallback_classify(user_message)

    def _call_llm(self, user_message: str) -> IntentResult:
        """调用 LLM Function Calling"""
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "tools": [INTENT_TOOL],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "classify_intent"},
                },
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        tool_calls = data["choices"][0]["message"].get("tool_calls", [])
        if not tool_calls:
            raise RuntimeError("LLM 未返回 tool_call")

        args = json.loads(tool_calls[0]["function"]["arguments"])
        intent_str = args.get("intent", "chitchat")

        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.CHITCHAT

        return IntentResult(
            intent=intent,
            confidence=float(args.get("confidence", 0.5)),
            reasoning=args.get("reasoning", ""),
            entities=args.get("entities", {}),
        )

    def _fallback_classify(self, user_message: str) -> IntentResult:
        """关键词降级分类（LLM 不可用时）"""
        text = user_message.lower()

        # 退货退款
        if any(
            kw in text for kw in ["退货", "退款", "换货", "退钱", "售后", "质量问题"]
        ):
            return IntentResult(
                intent=Intent.RETURN_REFUND,
                confidence=0.6,
                reasoning="关键词匹配: 退货/退款相关",
            )

        # 物流
        if any(kw in text for kw in ["物流", "快递", "配送", "发货", "运费", "到货"]):
            return IntentResult(
                intent=Intent.LOGISTICS,
                confidence=0.6,
                reasoning="关键词匹配: 物流相关",
            )

        # 订单
        if any(kw in text for kw in ["订单", "支付", "付款", "发票", "下单"]):
            return IntentResult(
                intent=Intent.ORDER_QUERY,
                confidence=0.6,
                reasoning="关键词匹配: 订单相关",
            )

        # 投诉
        if any(kw in text for kw in ["投诉", "不满", "差评", "举报", "建议"]):
            return IntentResult(
                intent=Intent.COMPLAINT,
                confidence=0.6,
                reasoning="关键词匹配: 投诉相关",
            )

        # 商品咨询
        if any(
            kw in text
            for kw in ["商品", "产品", "参数", "规格", "推荐", "哪个好", "怎么样"]
        ):
            return IntentResult(
                intent=Intent.PRODUCT_CONSULT,
                confidence=0.6,
                reasoning="关键词匹配: 商品咨询相关",
            )

        # 默认闲聊
        return IntentResult(
            intent=Intent.CHITCHAT,
            confidence=0.4,
            reasoning="未匹配到明确意图，归为闲聊",
        )


# ── 模块级单例 ──

_classifier_instance: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance
