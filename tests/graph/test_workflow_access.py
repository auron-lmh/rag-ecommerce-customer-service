"""模块13 工作流权限透传 — RAGState.access_level → retrieve_docs → search_with_degradation

注意: 只测节点级透传（monkeypatch 掉降级策略），不跑完整 LangGraph（依赖 LLM/Milvus）。
"""

from types import SimpleNamespace

from src.graph import workflow


class _RecordingStrategy:
    def __init__(self):
        self.last_access_level = None
        self.last_kwargs = None

    def search_with_degradation(
        self, query, secondary_query=None, top_k=5, use_rerank=True, **kwargs
    ):
        self.last_access_level = kwargs.get("access_level")
        self.last_kwargs = kwargs
        result = SimpleNamespace(
            response=SimpleNamespace(
                results=[
                    SimpleNamespace(
                        chunk_id="c",
                        text="文本",
                        score=0.9,
                        doc_type="pdf",
                        source_file="s.md",
                    )
                ],
                elapsed_ms=1,
            ),
            level=1,
            method="hybrid",
        )
        return result


def _state(access_level="public"):
    return {
        "query": "怎么退货",
        "rewritten_query": "怎么退货",
        "top_k": 5,
        "use_reranker": True,
        "history": [],
        "memory_context": "",
        "entities": {},
        "access_level": access_level,
    }


class TestWorkflowThreads:
    def test_retrieve_docs_forwards_from_state(self, monkeypatch):
        """retrieve_docs 把 state.access_level 透传给 search_with_degradation"""
        strategy = _RecordingStrategy()
        monkeypatch.setattr(
            workflow, "get_degradation_strategy", lambda retriever: strategy
        )
        # retrieve_docs 内用 from src.embedding.retriever import get_retriever，
        # 但 get_retriever() 只在传参时调用一次；这里换掉避免真实实例化
        monkeypatch.setattr("src.embedding.retriever.get_retriever", lambda: None)

        workflow.retrieve_docs(_state(access_level="member"))

        assert strategy.last_access_level == "member"

    def test_retrieve_docs_failsafe_public(self, monkeypatch):
        """state 无 access_level → 默认 public"""
        strategy = _RecordingStrategy()
        monkeypatch.setattr(
            workflow, "get_degradation_strategy", lambda retriever: strategy
        )
        monkeypatch.setattr("src.embedding.retriever.get_retriever", lambda: None)

        state = _state()
        state.pop("access_level")
        workflow.retrieve_docs(state)

        assert strategy.last_access_level == "public"
