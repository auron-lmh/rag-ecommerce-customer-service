"""测试脚本 - 查询检索"""

import json
import sys

import requests

API_BASE = "http://192.168.191.128:8000"


def test_query(query: str, top_k: int = 3):
    """测试查询"""
    print(f"\n{'='*60}")
    print(f"查询: {query}")
    print(f"{'='*60}")

    resp = requests.post(
        f"{API_BASE}/api/query", json={"query": query, "top_k": top_k}, timeout=30
    )

    data = resp.json()
    print(f"状态码: {resp.status_code}")
    print(f"结果数: {len(data.get('results', []))}")

    for i, r in enumerate(data.get("results", []), 1):
        print(f"\n--- 结果 {i} ---")
        print(f"分数: {r.get('score', 0):.4f}")
        print(f"来源: {r.get('source_file', '未知')}")
        print(f"文本: {r.get('text', '')[:200]}...")

    return data


if __name__ == "__main__":
    queries = [
        "Flink 是什么",
        "RAG 大模型",
        "退货流程",
        "A股市场分析",
    ]

    for q in queries:
        test_query(q)
        print()
