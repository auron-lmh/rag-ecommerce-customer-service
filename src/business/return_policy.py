"""退货/换货结构化政策 — 退货窗口 / 运费规则 / 退款时效 / 质量争议

行业痛点（clerk.io）: 退货是 AI 客服持续薄弱点——换尺码、退货窗口例外、
拆分退款，通用 FAQ 答不准。给 agent **真实结构化政策数据**（窗口/例外/运费规则），
而不是通用 FAQ。

与订单工具同模式（RAG + 工具 + 转人工 混合架构）:
  - 退货政策是**静态结构化知识**，从服务直接答——准确、不产生幻觉
  - 政策变更只改数据（_POLICY_LINES），不用重新训练/不用重灌向量库
  - 子场景检测只路由"定义清晰的政策问题"（窗口/运费/时效/质量），
    其余复杂问题仍走 RAG 知识库检索

使用:
    service = get_return_policy()
    reply, found = service.answer("退货运费谁出")
    scenario = service.detect_sub_scenario("质量问题怎么换货")  # ["quality", ...]
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════
# 结构化政策数据（变更只改这里）
# ═══════════════════════════════════════

_POLICY_LINES: dict[str, list[str]] = {
    "window": [
        "7天无理由退货：签收后7天内，商品未使用、吊牌完好、不影响二次销售即可申请退货。",
        "质量问题退货：签收后15天内可申请换货或退款。",
        "特殊品类不支持7天无理由：生鲜食品、定制商品、贴身衣物（内衣/袜）、已拆封的数码/化妆品，质量问题除外。",
    ],
    "freight": [
        "质量问题退货：运费由平台/商家承担（含运费险理赔）。",
        "非质量问题退货（不喜欢/买错）：运费由买家承担。",
        "购买时含运费险的订单，退货运费由保险公司赔付。",
    ],
    "refund_time": [
        "商品退回仓库验收合格后，退款在1-3个工作日内原路返回至您的支付账户（微信/支付宝/银行卡）。",
    ],
    "quality": [
        "质量问题请拍照/录视频保留证据，在订单详情页选择「质量问题」申请售后。",
        "审核通过后可换货或退款；发错货/漏发由商家承担运费补发或退款。",
    ],
    "process": [
        "退货流程：打开订单详情 → 点击「申请售后」 → 选择退货/换货 → 填写原因 → 提交后按提示寄回。",
        "退货有效期以商品页标注为准，超期后请提供订单号联系人工客服申请。",
    ],
}

# 子场景检测（优先级: 质量 > 运费 > 退款时效 > 退货窗口 > 流程）
_SUB_SCENARIO_DETECT: list[tuple[str, list[str]]] = [
    (
        "quality",
        [
            "质量问题",
            "瑕疵",
            "坏了",
            "破损",
            "开裂",
            "掉色",
            "发错",
            "漏发",
            "换货",
            "以次充好",
        ],
    ),
    ("freight", ["运费", "邮费", "谁出", "谁承担", "运费险"]),
    (
        "refund_time",
        ["几天到账", "多久到账", "什么时候到账", "退款时间", "何时退", "多长时间到"],
    ),
    (
        "window",
        [
            "几天内",
            "退货期限",
            "多久能退",
            "多久内",
            "几天能退",
            "还能退吗",
            "能不能退",
            "能退吗",
            "无理由",
            "7天",
            "七天",
        ],
    ),
    ("process", ["怎么退", "如何退", "退货流程", "怎么申请", "申请退货", "申请换货"]),
]


class ReturnPolicyService:
    """退货结构化政策服务

    对外暴露:
      - detect_sub_scenario(query) → list[str]（命中的子场景，空=未命中→走 RAG）
      - answer(query) → (reply, found)
    """

    def detect_sub_scenario(self, query: str) -> list[str]:
        """检测退货问题的子场景（质量/运费/时效/窗口/流程）"""
        if not query:
            return []
        hits = []
        for scenario, keywords in _SUB_SCENARIO_DETECT:
            if any(kw in query for kw in keywords):
                hits.append(scenario)
        return hits

    def answer(self, query: str) -> tuple[str, bool]:
        """生成退货政策回答

        Returns:
            (reply, found) — found=True 表示命中结构化政策
        """
        scenarios = self.detect_sub_scenario(query)
        if not scenarios:
            return "", False

        lines = []
        for s in scenarios:
            lines.extend(_POLICY_LINES[s])
        # 去重
        seen = set()
        unique = [line for line in lines if not (line in seen or seen.add(line))]
        logger.info("退货政策命中: %s", ",".join(scenarios))
        return "\n".join(unique), True


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_return_policy() -> ReturnPolicyService:
    """获取退货政策服务单例"""
    return ReturnPolicyService()
