"""模块5 查询扩展 — Multi-Query + HyDE

两种扩展策略:
  1. Multi-Query: 将一个 query 扩展为多个子 query，并行检索，合并结果
  2. HyDE (Hypothetical Document Embedding): 生成假设性文档，用文档的 embedding 检索

使用:
    expander = QueryExpander()
    expanded = expander.expand("iPhone 16 价格和参数")
    # → ["iPhone 16 价格", "iPhone 16 参数", "iPhone 16 规格"]
"""

import json
import logging
from typing import Optional

import requests

from src.config import settings

logger = logging.getLogger(__name__)

# Multi-Query 扩展 Prompt
MULTI_QUERY_PROMPT = """你是一个查询扩展专家。将用户的查询扩展为3-5个不同角度的子查询，用于向量检索。

规则:
1. 保留原始查询的核心语义
2. 从不同角度表达（同义词、具体化、泛化）
3. 每个子查询简洁明了，不超过30字
4. 输出JSON数组格式

用户查询: {query}

输出格式:
["子查询1", "子查询2", "子查询3"]"""

# HyDE 假设性文档生成 Prompt
HYDE_PROMPT = """你是一个电商知识库专家。根据用户的问题，生成一段假设性的回答文档。

规则:
1. 假设你知道答案，写出一段100-200字的回答
2. 使用专业的电商客服语气
3. 包含用户可能关心的关键信息点
4. 不要编造具体数字，用"XX"代替

用户问题: {query}

假设性回答:"""


class QueryExpander:
    """查询扩展器

    使用方式:
        expander = QueryExpander()

        # Multi-Query 扩展
        queries = expander.multi_query("iPhone 16 价格")
        # → ["iPhone 16 价格", "iPhone 16 售价", "iPhone 16 多少钱"]

        # HyDE 扩展
        doc = expander.hyde("iPhone 16 价格")
        # → "iPhone 16 是苹果公司最新推出的旗舰手机..."

        # 完整扩展（Multi-Query + HyDE）
        result = expander.expand("iPhone 16 价格")
        # → {"queries": [...], "hyde_doc": "..."}
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.default_model
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url

    def multi_query(self, query: str, num_queries: int = 3) -> list[str]:
        """Multi-Query 扩展

        将一个 query 扩展为多个子查询。

        Args:
            query: 原始查询
            num_queries: 期望的子查询数量

        Returns:
            子查询列表（包含原始查询）
        """
        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": MULTI_QUERY_PROMPT.format(query=query),
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                timeout=15,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            # 解析 JSON 数组
            if "[" in content and "]" in content:
                start = content.index("[")
                end = content.index("]") + 1
                queries = json.loads(content[start:end])
                if isinstance(queries, list):
                    # 确保原始查询在列表中
                    if query not in queries:
                        queries.insert(0, query)
                    return queries[:num_queries]

            # 解析失败，返回原始查询
            return [query]

        except Exception as e:
            logger.warning("Multi-Query 扩展失败: %s", e)
            return [query]

    def hyde(self, query: str) -> str:
        """HyDE (Hypothetical Document Embedding) 扩展

        生成假设性文档，用文档的 embedding 检索。

        Args:
            query: 原始查询

        Returns:
            假设性文档文本
        """
        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": HYDE_PROMPT.format(query=query),
                        }
                    ],
                    "temperature": 0.5,
                    "max_tokens": 300,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.warning("HyDE 扩展失败: %s", e)
            return query

    def expand(self, query: str) -> dict:
        """完整扩展（Multi-Query + HyDE）

        Args:
            query: 原始查询

        Returns:
            {
                "original": "原始查询",
                "queries": ["子查询1", "子查询2", ...],
                "hyde_doc": "假设性文档"
            }
        """
        queries = self.multi_query(query)
        hyde_doc = self.hyde(query)

        logger.info(
            "查询扩展: %s → %d 个子查询 + HyDE文档",
            query[:50],
            len(queries),
        )

        return {
            "original": query,
            "queries": queries,
            "hyde_doc": hyde_doc,
        }


# ── 模块级单例 ──

_expander_instance: Optional[QueryExpander] = None


def get_query_expander() -> QueryExpander:
    """获取 QueryExpander 单例"""
    global _expander_instance
    if _expander_instance is None:
        _expander_instance = QueryExpander()
    return _expander_instance
