"""模块: LangGraph 图编排 — 核心业务流程

使用:
    from src.graph import get_workflow
    workflow = get_workflow()
    result = workflow.invoke({"query": "怎么退货？"})
"""

from .workflow import RAGWorkflow, get_workflow

__all__ = [
    "RAGWorkflow",
    "get_workflow",
]
