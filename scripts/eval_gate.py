"""评测质量门禁 — 跑评估数据集，检查关键指标阈值，不达标 exit 1

用法（在部署环境 VM 上跑，需 Milvus + 知识库 + API Key）:
    python scripts/eval_gate.py                    # 默认阈值
    python scripts/eval_gate.py --recall 0.70      # 自定义 Recall@5 阈值
    python scripts/eval_gate.py --limit 10         # 冒烟（只跑前 10 条）
    python scripts/eval_gate.py --with-generation  # 完整 RAG（检索+生成）

用途:
    - 改代码后跑一遍，确保检索质量没回退
    - 面试必问「怎么保证改代码后准确率不降」→ 这就是答案：黄金测试集 + 质量门禁
    - 可接入 CI/CD（指标低于阈值 → 阻止发布）

退出码:
    0 = 全部指标达标
    1 = 有指标低于阈值（阻止发布）
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

# 默认质量门禁阈值（略低于 README 基准 Recall@5=0.755 / MRR=0.725，留波动空间）
DEFAULT_THRESHOLDS = {
    "recall@5": 0.70,
    "mrr": 0.65,
    "precision@5": 0.55,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 评测质量门禁")
    parser.add_argument("--recall", type=float, default=None, help="Recall@5 阈值")
    parser.add_argument("--mrr", type=float, default=None, help="MRR 阈值")
    parser.add_argument(
        "--precision", type=float, default=None, help="Precision@5 阈值"
    )
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全部）")
    parser.add_argument(
        "--with-generation", action="store_true", help="完整 RAG（检索+生成）"
    )
    args = parser.parse_args()

    thresholds = {
        "recall@5": (
            args.recall if args.recall is not None else DEFAULT_THRESHOLDS["recall@5"]
        ),
        "mrr": args.mrr if args.mrr is not None else DEFAULT_THRESHOLDS["mrr"],
        "precision@5": (
            args.precision
            if args.precision is not None
            else DEFAULT_THRESHOLDS["precision@5"]
        ),
    }

    from src.evaluation import get_evaluator

    evaluator = get_evaluator()
    test_cases = evaluator.load_dataset()
    if args.limit:
        test_cases = test_cases[: args.limit]
    if not test_cases:
        print("❌ 评估数据集为空")
        sys.exit(1)

    print(f"\n📊 质量门禁: {len(test_cases)} 条用例")

    # 逐条评测 + 容错（一条失败不拖垮整批，记录后继续）
    results = []
    failed = 0
    for i, tc in enumerate(test_cases):
        try:
            if args.with_generation:
                r = evaluator.evaluate_query_with_generation(tc)
            else:
                r = evaluator.evaluate_query(tc)
            results.append(r)
        except Exception as e:
            failed += 1
            print(f"  ⚠️ 用例失败 [{i + 1}] {tc.question[:30]}: {e}")

    if not results:
        print("❌ 全部用例失败，无法评测")
        sys.exit(1)

    total = len(results)
    avg = {
        "recall@5": sum(r.recall_at_5 for r in results) / total,
        "mrr": sum(r.mrr for r in results) / total,
        "precision@5": sum(r.precision_at_5 for r in results) / total,
    }

    # 打印指标 + 判定
    print("\n" + "=" * 52)
    print("  🎯 质量门禁判定")
    print("=" * 52)
    passed = True
    for key, value in avg.items():
        threshold = thresholds[key]
        ok = value >= threshold
        if not ok:
            passed = False
        mark = "✅" if ok else "❌"
        print(f"  {mark} {key:<12} {value:.4f}  (阈值 ≥{threshold})")

    if failed:
        print(f"  ⚠️ 失败用例: {failed}/{len(test_cases)}")
    print("=" * 52)

    if not passed:
        print("\n❌ 质量门禁未通过：有指标低于阈值，阻止发布。")
        print("   请检查: 1) 检索逻辑是否回退  2) 知识库是否完整  3) 阈值是否过严")
        sys.exit(1)

    print("\n✅ 质量门禁通过：核心检索指标全部达标。")


if __name__ == "__main__":
    main()
