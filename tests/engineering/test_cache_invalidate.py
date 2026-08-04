"""缓存定向失效测试 — 知识更新后清检索缓存（实时性闭环）"""

from src.engineering.cache import CacheManager, MemoryCache


class TestClearByPrefix:
    def test_memory_cache_clear_by_prefix(self):
        c = MemoryCache()
        c.set("query:aaa", "v1")
        c.set("query:bbb", "v2")
        c.set("emb:ccc", "v3")
        c.set("llm:ddd", "v4")

        removed = c.clear_by_prefix("query:")
        assert removed == 2
        assert c.get("query:aaa") is None
        assert c.get("query:bbb") is None
        # 非目标前缀不受影响
        assert c.get("emb:ccc") == "v3"
        assert c.get("llm:ddd") == "v4"

    def test_clear_by_prefix_no_match(self):
        c = MemoryCache()
        c.set("llm:aaa", "v1")
        assert c.clear_by_prefix("query:") == 0

    def test_clear_by_prefix_empty(self):
        c = MemoryCache()
        assert c.clear_by_prefix("query:") == 0


class TestClearQueryCache:
    def test_manager_clears_only_query_layer(self):
        cm = CacheManager(backend=MemoryCache())
        cm.set_query_result("怎么退货？", {"results": []})
        cm.set_embedding("某文本", [0.1, 0.2])
        cm.set_llm_response("某prompt", "回答")

        removed = cm.clear_query_cache()
        assert removed >= 1
        # query 层已清
        assert cm.get_query_result("怎么退货？") is None
        # embedding / LLM 层保留
        assert cm.get_embedding("某文本") == [0.1, 0.2]
        assert cm.get_llm_response("某prompt") == "回答"

    def test_cache_keyed_by_composite_cleared(self):
        """retriever 用的复合 cache_key 也应被前缀清理命中"""
        cm = CacheManager(backend=MemoryCache())
        cache_key = "怎么退货？:5:True:True::None:0.7"
        cm.set_query_result(cache_key, {"results": [1]})
        assert cm.get_query_result(cache_key) is not None
        cm.clear_query_cache()
        assert cm.get_query_result(cache_key) is None
