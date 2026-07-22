"""模块14: 测试与评估 — 评测数据集 + 自动化评测脚本

使用:
    from src.evaluation import get_evaluator
    evaluator = get_evaluator()
    result = evaluator.evaluate_query("怎么退货", ground_truth_answer="...")
"""

from .evaluator import RetrievalEvaluator, get_evaluator
from .metrics import calculate_faithfulness, calculate_mrr, calculate_recall

__all__ = [
    "RetrievalEvaluator",
    "get_evaluator",
    "calculate_recall",
    "calculate_mrr",
    "calculate_faithfulness",
]
