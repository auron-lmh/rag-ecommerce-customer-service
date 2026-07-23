"""模块14 检索评估器 — 自动化评测脚本

评估指标:
    recall@K        → Embedding 语义相似度（替代子串匹配）
    mrr             → Embedding 语义相似度排名
    faithfulness    → LLM G-Eval（精确模式）/ Embedding 相似度（快速模式）

使用:
    evaluator = RetrievalEvaluator(retriever)
    results = evaluator.evaluate_dataset(test_cases)
    print(results["recall@5"])

    # 精确模式（使用 LLM 评估忠实度）
    results = evaluator.evaluate_dataset(test_cases, use_llm_eval=True)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.config import settings

from .metrics import (
    calculate_faithfulness,
    calculate_keyword_coverage,
    calculate_latency_score,
    calculate_mrr,
    calculate_recall,
)

logger = logging.getLogger(__name__)

# 评测数据集路径
EVAL_DATASET_PATH = settings.data_dir / "eval_dataset.json"


@dataclass
class TestCase:
    """测试用例"""

    question: str
    ground_truth_answer: str
    must_contain_keywords: list[str] = field(default_factory=list)
    intent: str = ""
    difficulty: str = "medium"  # easy / medium / hard


@dataclass
class EvalResult:
    """单条评测结果"""

    question: str
    recall_at_5: float
    mrr: float
    faithfulness: float
    keyword_coverage: float
    latency_ms: float
    latency_score: float
    hallucination_detected: bool
    correction_rounds: int
    answer: str = ""
    retrieved_docs: list[str] = field(default_factory=list)


class RetrievalEvaluator:
    """检索评估器

    使用方式:
        evaluator = RetrievalEvaluator(retriever)
        results = evaluator.evaluate_dataset(test_cases)
    """

    def __init__(self, retriever=None):
        self._retriever = retriever

    @property
    def retriever(self):
        if self._retriever is None:
            from src.embedding.retriever import get_retriever

            self._retriever = get_retriever()
        return self._retriever

    def evaluate_query(
        self, test_case: TestCase, use_llm_eval: bool = False
    ) -> EvalResult:
        """评测单条查询（仅检索，不生成）

        Args:
            test_case: 测试用例
            use_llm_eval: 是否使用 LLM 评估忠实度（默认 False 用快速模式）

        Returns:
            EvalResult
        """
        t0 = time.time()

        # 检索
        search_response = self.retriever.search(
            query=test_case.question,
            top_k=5,
            use_rerank=True,
        )
        latency_ms = (time.time() - t0) * 1000

        retrieved_docs = [r.text for r in search_response.results]

        # 计算指标
        recall_at_5 = calculate_recall(
            retrieved_docs, test_case.ground_truth_answer, k=5
        )
        mrr = calculate_mrr(retrieved_docs, test_case.ground_truth_answer)
        faithfulness = calculate_faithfulness(
            test_case.ground_truth_answer,
            retrieved_docs,
            use_llm=use_llm_eval,
        )
        keyword_coverage = calculate_keyword_coverage(
            test_case.ground_truth_answer,
            test_case.must_contain_keywords,
        )
        latency_score = calculate_latency_score(latency_ms)

        return EvalResult(
            question=test_case.question,
            recall_at_5=recall_at_5,
            mrr=mrr,
            faithfulness=faithfulness,
            keyword_coverage=keyword_coverage,
            latency_ms=latency_ms,
            latency_score=latency_score,
            hallucination_detected=False,
            correction_rounds=0,
            answer=test_case.ground_truth_answer,
            retrieved_docs=retrieved_docs[:3],
        )

    def evaluate_query_with_generation(
        self, test_case: TestCase, use_llm_eval: bool = False
    ) -> EvalResult:
        """评测单条查询（完整 RAG 流程：检索 + 生成）

        关键修复: 评测实际生成的回答，而非标准答案

        Args:
            test_case: 测试用例
            use_llm_eval: 是否使用 LLM 评估忠实度

        Returns:
            EvalResult
        """
        t0 = time.time()

        # 使用 SelfCorrector 运行完整 RAG 流程
        from src.generation import get_corrector

        corrector = get_corrector(self.retriever)

        result = corrector.generate_with_correction(
            query=test_case.question,
            top_k=5,
            use_rerank=True,
        )
        latency_ms = (time.time() - t0) * 1000

        generated_answer = result.answer
        retrieved_docs = (
            [r.text for r in result.sources] if hasattr(result, "sources") else []
        )

        # 计算指标（使用实际生成的回答）
        recall_at_5 = calculate_recall(
            retrieved_docs, test_case.ground_truth_answer, k=5
        )
        mrr = calculate_mrr(retrieved_docs, test_case.ground_truth_answer)

        # 关键: 用实际生成的回答评估忠实度，而非标准答案
        faithfulness = calculate_faithfulness(
            generated_answer,
            retrieved_docs,
            use_llm=use_llm_eval,
        )
        keyword_coverage = calculate_keyword_coverage(
            generated_answer,
            test_case.must_contain_keywords,
        )
        latency_score = calculate_latency_score(latency_ms)

        return EvalResult(
            question=test_case.question,
            recall_at_5=recall_at_5,
            mrr=mrr,
            faithfulness=faithfulness,
            keyword_coverage=keyword_coverage,
            latency_ms=latency_ms,
            latency_score=latency_score,
            hallucination_detected=result.was_corrected,
            correction_rounds=result.correction_rounds,
            answer=generated_answer,
            retrieved_docs=retrieved_docs[:3],
        )

    def evaluate_dataset(
        self,
        test_cases: list[TestCase],
        use_llm_eval: bool = False,
        with_generation: bool = False,
    ) -> dict:
        """评测数据集

        Args:
            test_cases: 测试用例列表
            use_llm_eval: 是否使用 LLM 评估忠实度（默认 False 用快速 Embedding 模式）
            with_generation: 是否运行完整 RAG 流程（检索+生成），默认 False 仅检索

        Returns:
            评测结果汇总
        """
        eval_mode = "LLM 精确模式" if use_llm_eval else "Embedding 快速模式"
        gen_mode = "完整 RAG" if with_generation else "仅检索"
        logger.info("开始评测 %d 条用例 (%s, %s)", len(test_cases), eval_mode, gen_mode)

        results = []
        for i, tc in enumerate(test_cases):
            logger.info("评测 %d/%d: %s", i + 1, len(test_cases), tc.question[:50])
            if with_generation:
                result = self.evaluate_query_with_generation(
                    tc, use_llm_eval=use_llm_eval
                )
            else:
                result = self.evaluate_query(tc, use_llm_eval=use_llm_eval)
            results.append(result)

        # 汇总
        total = len(results)
        if total == 0:
            return {"error": "无测试用例"}

        avg_recall = sum(r.recall_at_5 for r in results) / total
        avg_mrr = sum(r.mrr for r in results) / total
        avg_faithfulness = sum(r.faithfulness for r in results) / total
        avg_keyword_coverage = sum(r.keyword_coverage for r in results) / total
        avg_latency = sum(r.latency_ms for r in results) / total
        avg_latency_score = sum(r.latency_score for r in results) / total

        return {
            "total_cases": total,
            "recall@5": round(avg_recall, 4),
            "mrr": round(avg_mrr, 4),
            "faithfulness": round(avg_faithfulness, 4),
            "keyword_coverage": round(avg_keyword_coverage, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "latency_score": round(avg_latency_score, 4),
            "details": [
                {
                    "question": r.question,
                    "recall@5": r.recall_at_5,
                    "mrr": r.mrr,
                    "latency_ms": round(r.latency_ms, 1),
                }
                for r in results
            ],
        }

    def load_dataset(self, path: Optional[Path] = None) -> list[TestCase]:
        """加载评测数据集"""
        dataset_path = path or EVAL_DATASET_PATH
        if not dataset_path.exists():
            return self._create_default_dataset()

        with open(dataset_path, encoding="utf-8") as f:
            data = json.load(f)

        return [
            TestCase(
                question=tc["question"],
                ground_truth_answer=tc["ground_truth_answer"],
                must_contain_keywords=tc.get("must_contain_keywords", []),
                intent=tc.get("intent", ""),
                difficulty=tc.get("difficulty", "medium"),
            )
            for tc in data
        ]

    def _create_default_dataset(self) -> list[TestCase]:
        """创建默认评测数据集（电商场景）"""
        return [
            TestCase(
                question="怎么退货？",
                ground_truth_answer="退货流程",
                must_contain_keywords=["退货", "流程"],
                intent="return_refund",
                difficulty="easy",
            ),
            TestCase(
                question="退货时限是几天？",
                ground_truth_answer="退货时限",
                must_contain_keywords=["退货", "天"],
                intent="return_refund",
                difficulty="medium",
            ),
            TestCase(
                question="退款多久到账？",
                ground_truth_answer="退款到账时间",
                must_contain_keywords=["退款", "到账"],
                intent="return_refund",
                difficulty="medium",
            ),
            TestCase(
                question="这个手机壳怎么样？",
                ground_truth_answer="手机壳",
                must_contain_keywords=["手机壳"],
                intent="product_consult",
                difficulty="easy",
            ),
            TestCase(
                question="快递到哪了？",
                ground_truth_answer="物流",
                must_contain_keywords=["快递", "物流"],
                intent="logistics",
                difficulty="easy",
            ),
        ]

    def save_dataset(
        self, test_cases: list[TestCase], path: Optional[Path] = None
    ) -> None:
        """保存评测数据集"""
        dataset_path = path or EVAL_DATASET_PATH
        dataset_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "question": tc.question,
                "ground_truth_answer": tc.ground_truth_answer,
                "must_contain_keywords": tc.must_contain_keywords,
                "intent": tc.intent,
                "difficulty": tc.difficulty,
            }
            for tc in test_cases
        ]

        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("评测数据集已保存: %s (%d 条)", dataset_path, len(test_cases))


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_evaluator() -> RetrievalEvaluator:
    return RetrievalEvaluator()
