"""电商领域同义词表 — 关键词检索（BM25）的同义词扩展

背景: BM25 依赖关键词精确匹配，用户口语（"退钱"）与知识库术语（"退款"）
不一致会导致漏召回。同义词扩展把口语词映射到标准术语，提升关键词召回。

使用:
    from src.embedding.synonyms import expand_query_with_synonyms
    q = expand_query_with_synonyms("怎么退钱")  # → "怎么退钱 退款 返款"
"""

ECOMMERCE_SYNONYMS: dict[str, list[str]] = {
    "退款": ["退钱", "返款", "退款到账"],
    "退货": ["退换", "换货", "退换货"],
    "优惠券": ["红包", "券", "满减", "折扣券"],
    "物流": ["快递", "配送", "发货", "寄送"],
    "运费": ["邮费", "快递费", "配送费"],
    "订单": ["下单", "购买", "成交"],
    "到账": ["到款", "入账"],
    "商品": ["产品", "货品", "货物"],
    "会员": ["VIP", "等级会员"],
    "积分": ["会员分", "奖励分"],
    "客服": ["人工", "售后", "坐席"],
    "投诉": ["举报", "差评", "维权"],
    "发票": ["票据", "报销凭证"],
    "保修": ["质保", "三包", "售后保障"],
    "签收": ["收货", "签单"],
    "支付": ["付款", "结账", "买单"],
    "活动": ["促销", "大促", "优惠活动"],
    "规格": ["参数", "配置"],
    "库存": ["现货", "有货"],
}


def expand_query_with_synonyms(
    query: str, synonyms: dict[str, list[str]] | None = None
) -> str:
    """把 query 命中的同义词拼到 query 后面，增加 BM25 关键词召回。

    - 只做「确定性词表映射」，不做 LLM（零成本、零延迟）
    - query 含标准词或任一变体时，补充所有未出现的等价词
    """
    table = synonyms if synonyms is not None else ECOMMERCE_SYNONYMS
    extra: list[str] = []
    for standard, variants in table.items():
        hit = standard in query or any(v in query for v in variants)
        if hit:
            for w in [standard] + variants:
                if w not in query and w not in extra:
                    extra.append(w)
    if extra:
        return f"{query} {' '.join(extra)}"
    return query
