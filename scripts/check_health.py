"""检查 API 健康状态"""

import json

import requests

API_BASE = "http://192.168.191.128:8000"


def check_health():
    """检查 API 状态"""
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=10)
        data = resp.json()
        print("=" * 60)
        print("API 健康检查")
        print("=" * 60)
        print(f"状态: {data.get('status')}")
        print(f"Milvus: {data.get('milvus')}")
        print(f"Embedder: {data.get('embedder')}")
        print(f"Reranker: {data.get('reranker')}")
        print(f"Collection: {data.get('collection', {}).get('collection_name')}")
        print(f"向量数: {data.get('collection', {}).get('total_vectors', 0)}")
        return True
    except Exception as e:
        print(f"API 检查失败: {e}")
        return False


if __name__ == "__main__":
    check_health()
