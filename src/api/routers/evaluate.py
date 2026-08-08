"""模块14 评估路由 — POST /api/evaluate

自动化评测：评测数据集 + 指标计算
"""

import logging

from fastapi import APIRouter, Depends

from src.api.auth import CurrentUser
from src.api.deps import get_retriever, require_admin
from src.embedding.retriever import Retriever
from src.evaluation import get_evaluator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["评估"])


@router.post("/evaluate")
async def evaluate(
    retriever: Retriever = Depends(get_retriever),
    admin: CurrentUser = Depends(require_admin),
) -> dict:
    """运行自动化评测（仅管理员，面向完整知识库全量权限）

    使用默认评测数据集（5条电商场景用例），
    计算 Recall@5, MRR, Faithfulness, Latency 等指标。
    """
    evaluator = get_evaluator()
    evaluator._retriever = retriever

    test_cases = evaluator.load_dataset()
    results = evaluator.evaluate_dataset(test_cases)

    return results


@router.post("/evaluate/query")
async def evaluate_query(
    question: str,
    ground_truth: str,
    retriever: Retriever = Depends(get_retriever),
    admin: CurrentUser = Depends(require_admin),
) -> dict:
    """评测单条查询（仅管理员，全量权限）"""
    from src.evaluation.evaluator import TestCase

    evaluator = get_evaluator()
    evaluator._retriever = retriever

    test_case = TestCase(
        question=question,
        ground_truth_answer=ground_truth,
    )
    result = evaluator.evaluate_query(test_case, access_level="vip")

    return {
        "question": result.question,
        "recall@5": result.recall_at_5,
        "mrr": result.mrr,
        "faithfulness": result.faithfulness,
        "keyword_coverage": result.keyword_coverage,
        "latency_ms": round(result.latency_ms, 1),
    }
